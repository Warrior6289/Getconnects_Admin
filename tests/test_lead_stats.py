import datetime

def test_get_leads_by_campaign(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign1 = app_module.Campaign(id="camp1", campaign_name="Camp1", client=client)
    campaign2 = app_module.Campaign(id="camp2", campaign_name="Camp2", client=client)
    session.add_all([client, campaign1, campaign2])
    session.commit()

    session.add(app_module.Lead(name="Lead1", campaign_id=campaign1.id, client_id=client.id))
    session.commit()

    stats = app_module.get_leads_by_campaign()
    # convert list to dict for easy assertions
    data = {item["campaign"]: item["leads"] for item in stats}
    assert data["Camp1"] == 1
    assert data["Camp2"] == 0
