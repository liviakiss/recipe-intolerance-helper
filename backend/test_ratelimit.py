"""Tests for the rate limiter: the counting itself, then the real endpoints."""
import pytest

from app.ratelimit import RateLimiter, client_ip


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeRequest:
    def __init__(self, headers=None, host="10.0.0.1"):
        self.headers = headers or {}
        self.client = type("Client", (), {"host": host})() if host else None


# ---------- the counting ----------

def test_calls_up_to_the_limit_are_allowed():
    limiter = RateLimiter(max_calls=3, window_seconds=60, clock=FakeClock())

    assert [limiter.check("a") for _ in range(3)] == [None, None, None]


def test_the_call_over_the_limit_is_refused_with_a_wait_time():
    clock = FakeClock()
    limiter = RateLimiter(max_calls=2, window_seconds=60, clock=clock)
    limiter.check("a")
    clock.now += 10
    limiter.check("a")
    clock.now += 5

    # The first call was 15 seconds ago, so it expires in 45.
    assert limiter.check("a") == 45


def test_calls_are_allowed_again_once_the_window_has_passed():
    clock = FakeClock()
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=clock)
    limiter.check("a")
    assert limiter.check("a") is not None

    clock.now += 61

    assert limiter.check("a") is None


def test_each_visitor_has_their_own_count():
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=FakeClock())
    limiter.check("alice")

    assert limiter.check("alice") is not None
    assert limiter.check("bob") is None


def test_a_refused_call_is_not_counted():
    clock = FakeClock()
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=clock)
    limiter.check("a")
    for _ in range(20):
        limiter.check("a")  # all refused

    clock.now += 61

    # If refusals had counted, this would still be blocked.
    assert limiter.check("a") is None


def test_reset_forgets_everything():
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=FakeClock())
    limiter.check("a")

    limiter.reset()

    assert limiter.check("a") is None


# ---------- who is the visitor ----------

def test_the_visitor_is_the_first_forwarded_address():
    request = FakeRequest({"x-forwarded-for": "203.0.113.7, 10.1.1.1"})

    assert client_ip(request) == "203.0.113.7"


def test_without_a_proxy_header_the_connection_address_is_used():
    assert client_ip(FakeRequest(host="192.0.2.5")) == "192.0.2.5"


def test_a_request_with_no_address_at_all_still_gets_a_key():
    assert client_ip(FakeRequest(host=None)) == "unknown"


# ---------- the real endpoints ----------

def post_login(client, headers=None):
    return client.post("/login", json={"email": "a@b.com", "password": "wrong"}, headers=headers)


def test_login_is_limited_per_visitor(client):
    statuses = [post_login(client).status_code for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_a_limited_response_says_when_to_retry(client):
    for _ in range(10):
        post_login(client)

    response = post_login(client)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert "detail" in response.json()


def test_one_visitor_being_limited_does_not_block_another(client):
    for _ in range(10):
        post_login(client, headers={"X-Forwarded-For": "198.51.100.1"})

    blocked = post_login(client, headers={"X-Forwarded-For": "198.51.100.1"})
    other = post_login(client, headers={"X-Forwarded-For": "198.51.100.2"})

    assert blocked.status_code == 429
    assert other.status_code == 401


def test_scan_is_limited_per_visitor(client):
    def scan():
        return client.post("/scan-recipe", files={"file": ("n.txt", b"x", "text/plain")})

    statuses = [scan().status_code for _ in range(11)]

    assert statuses[:10] == [415] * 10  # past the limiter, turned away for being no image
    assert statuses[10] == 429


def test_scan_has_a_cap_across_all_visitors(client, monkeypatch):
    from app import main
    monkeypatch.setattr(main.scan_everyone, "max_calls", 3)

    def scan(ip):
        return client.post(
            "/scan-recipe",
            files={"file": ("n.txt", b"x", "text/plain")},
            headers={"X-Forwarded-For": ip},
        ).status_code

    # Four different visitors, one scan each: the fourth hits the shared cap.
    assert [scan(f"203.0.113.{n}") for n in range(1, 5)] == [415, 415, 415, 429]


def test_ordinary_endpoints_are_not_limited(client):
    assert all(client.get("/ingredient-tags").status_code == 200 for _ in range(50))
