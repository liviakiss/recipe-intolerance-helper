"""Tests for POST /check-recipe, the paste-a-recipe endpoint."""


def test_pasted_recipe_is_checked(client, tag_ids, add_ingredient):
    add_ingredient("butter", ["dairy", "lactose"], substitute=("vegan margarine", "Use in equal amounts."))
    add_ingredient("sugar", [])

    response = client.post("/check-recipe", json={
        "raw_text": "100 g butter\n50 g sugar\n1 dragon egg",
        "active_tag_ids": [tag_ids["dairy"]],
    })

    assert response.status_code == 200
    results = response.json()
    assert [r["status"] for r in results] == ["flagged", "safe", "unrecognized"]
    assert results[0]["substitute"]["name"] == "vegan margarine"
    assert sorted(results[0]["matched_tags"]) == ["dairy", "lactose"]


def test_the_request_needs_both_fields(client):
    assert client.post("/check-recipe", json={"raw_text": "2 eggs"}).status_code == 422
    assert client.post("/check-recipe", json={"active_tag_ids": []}).status_code == 422


def test_empty_recipe_returns_an_empty_list(client):
    response = client.post("/check-recipe", json={"raw_text": "", "active_tag_ids": []})

    assert response.status_code == 200
    assert response.json() == []
