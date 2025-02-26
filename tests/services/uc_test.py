from app.services import uc_service


def test_user_batch():
    print(uc_service.user_batch(usercodes=["29406069"]))
    print(uc_service.user_batch(ids=["1000000029406069"]))
