from unittest import TestCase

import pytest
from neuro_san.test.unittest.dynamic_hocon_unit_tests import DynamicHoconUnitTests

# Data-driven fixtures, relative to tests/fixtures/. Schema:
# https://github.com/cognizant-ai-lab/neuro-san/blob/main/docs/test_case_hocon_reference.md
FIXTURES = [
    "docs_qa/assistant/context7_react_use_effect_cleanup.hocon",
    "docs_qa/assistant/ms_learn_azure_managed_identity.hocon",
    "docs_qa/assistant/context7_typescript_partial.hocon",
    "docs_qa/assistant/ms_learn_github_actions_azure_deploy.hocon",
    "docs_qa/assistant/context7_github_actions_branch_filter.hocon",
    "docs_qa/assistant/cross_domain_react_azure_functions.hocon",
    "docs_qa/assistant/out_of_scope_weather.hocon",
    "docs_qa/assistant/follow_up_storage_account_powershell.hocon",
]

fixture_runner = DynamicHoconUnitTests(__file__, path_to_basis="../fixtures")


@pytest.mark.integration
@pytest.mark.parametrize("test_hocon", FIXTURES, ids=DynamicHoconUnitTests.test_name_from_hocon_file)
def test_network_fixture(test_hocon: str):
    test_name = DynamicHoconUnitTests.test_name_from_hocon_file(test_hocon)
    fixture_runner.one_test_hocon(TestCase(), test_name, test_hocon)
