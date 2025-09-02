from app.config.apollo_configs import retrieval_default_config


def test_retrieval_config():
    assert retrieval_default_config.get_retrieve_mode() == 'semantic'
    assert len(retrieval_default_config.get_plugins()) == 1
