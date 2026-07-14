from .status_mapping import API_TO_DB_STATUS, DB_TO_API_STATUS, API_STATUS_CHOICES


class TestStatusMapping:
    def test_api_to_db_completeness(self):
        assert API_TO_DB_STATUS['RUNNING'] == 'in_progress'
        assert API_TO_DB_STATUS['SUCCESS'] == 'success'
        assert API_TO_DB_STATUS['FAILED'] == 'error'

    def test_db_to_api_is_inverse(self):
        for api, db in API_TO_DB_STATUS.items():
            assert DB_TO_API_STATUS[db] == api

    def test_choices_list_matches_mapping(self):
        assert set(API_STATUS_CHOICES) == set(API_TO_DB_STATUS.keys())