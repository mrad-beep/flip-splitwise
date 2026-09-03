def test_full_group_flow(client):
    # Create three users.
    a = client.post("/api/users", json={"name": "Alice"}).get_json()
    b = client.post("/api/users", json={"name": "Bob"}).get_json()
    c = client.post("/api/users", json={"name": "Cara"}).get_json()

    # Create a group with all three.
    group = client.post(
        "/api/groups",
        json={"name": "Trip", "member_ids": [a["id"], b["id"], c["id"]]},
    ).get_json()
    assert len(group["members"]) == 3

    # Alice pays 90 for something split equally three ways.
    resp = client.post(
        f"/api/groups/{group['id']}/expenses",
        json={"description": "Hotel", "amount": 90, "paid_by": a["id"]},
    )
    assert resp.status_code == 201
    expense = resp.get_json()
    assert sum(s["amount"] for s in expense["splits"]) == 90

    balances = client.get(f"/api/groups/{group['id']}/balances").get_json()
    net_by_name = {n["user"]["name"]: n["amount"] for n in balances["net"]}
    assert net_by_name["Alice"] == 60  # paid 90, owes 30
    assert net_by_name["Bob"] == -30
    assert net_by_name["Cara"] == -30

    # Bob settles up with Alice.
    resp = client.post(
        f"/api/groups/{group['id']}/settlements",
        json={"from_user": b["id"], "to_user": a["id"], "amount": 30},
    )
    assert resp.status_code == 201

    balances = client.get(f"/api/groups/{group['id']}/balances").get_json()
    net_by_name = {n["user"]["name"]: n["amount"] for n in balances["net"]}
    assert "Bob" not in net_by_name  # settled to zero, filtered out
    assert net_by_name["Alice"] == 30
    assert net_by_name["Cara"] == -30


def test_expense_rejects_non_member_payer(client):
    a = client.post("/api/users", json={"name": "Alice"}).get_json()
    outsider = client.post("/api/users", json={"name": "Dave"}).get_json()
    group = client.post(
        "/api/groups", json={"name": "Trip", "member_ids": [a["id"]]}
    ).get_json()

    resp = client.post(
        f"/api/groups/{group['id']}/expenses",
        json={"description": "Snacks", "amount": 20, "paid_by": outsider["id"]},
    )
    assert resp.status_code == 400


def test_expense_rejects_non_positive_amount(client):
    a = client.post("/api/users", json={"name": "Alice"}).get_json()
    group = client.post(
        "/api/groups", json={"name": "Trip", "member_ids": [a["id"]]}
    ).get_json()

    resp = client.post(
        f"/api/groups/{group['id']}/expenses",
        json={"description": "Snacks", "amount": -5, "paid_by": a["id"]},
    )
    assert resp.status_code == 400
