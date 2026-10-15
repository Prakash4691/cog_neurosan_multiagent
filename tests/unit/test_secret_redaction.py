"""Runs the Coordinator's redaction middleware, exactly as the deployed assistant network declares it, on sample Error
Logs. This proves the detector regexes redact (ADR 0002). The planted-secret fixture proves they are wired in."""

import importlib

import pytest
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from neuro_san.internals.graph.persistence.agent_network_restorer import AgentNetworkRestorer

# Built in pieces so secret scanners don't flag this file.
PEM_BEGIN = "-----BEGIN " + "PRIVATE KEY-----"
PEM_END = "-----END " + "PRIVATE KEY-----"
RSA_PEM_BEGIN = "-----BEGIN RSA " + "PRIVATE KEY-----"
RSA_PEM_END = "-----END RSA " + "PRIVATE KEY-----"
# 88 characters ending in "==", the shape of a real Azure storage account key.
FAKE_AZURE_ACCOUNT_KEY = "Zm9vYmFy" * 10 + "Zm9vYm" + "=="
FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


def load_coordinator_middleware() -> list[dict]:
    network = AgentNetworkRestorer(registry_dir="registries").restore("docs_qa/assistant.hocon")
    coordinator = network.get_config()["tools"][0]
    assert coordinator["name"] == "Coordinator"
    return coordinator["middleware"]


def create_middleware(entry: dict) -> AgentMiddleware:
    # The same class path and args that neuro-san instantiates for the Coordinator.
    module_name, class_name = entry["class"].rsplit(".", 1)
    middleware_class = getattr(importlib.import_module(module_name), class_name)
    return middleware_class(**entry["args"])


MIDDLEWARE = [create_middleware(entry) for entry in load_coordinator_middleware()]


def redact_conversation(messages: list) -> list:
    """Runs every middleware's before_model hook in order, as the agent does before each Coordinator LLM call."""
    state = {"messages": messages}
    for middleware in MIDDLEWARE:
        update = middleware.before_model(state, None)
        if update:
            state = update
    return state["messages"]


def redact(user_message: str) -> str:
    return redact_conversation([HumanMessage(user_message)])[-1].content


def test_coordinator_runs_seven_redacting_pii_middleware_entries():
    entries = load_coordinator_middleware()
    assert len(entries) == 7
    for entry in entries:
        assert entry["class"] == "middleware.docs_qa.all_turns_pii_middleware.AllTurnsPIIMiddleware"
        assert entry["args"]["strategy"] == "redact"
        assert entry["args"]["apply_to_input"] is True

    pii_types = {entry["args"]["pii_type"] for entry in entries}
    assert pii_types == {
        "connection_string",
        "bearer_token",
        "cloud_key",
        "secret_assignment",
        "private_key",
        "internal_host",
        "email",
    }
    # email uses LangChain's built-in detector; every custom type brings its own regex.
    for entry in entries:
        has_detector = "detector" in entry["args"]
        assert has_detector == (entry["args"]["pii_type"] != "email")


SECRETS = [
    # (log line, secret that must disappear, expected replacement)
    pytest.param(
        "Server=tcp:contoso-sql.database.windows.net,1433;Initial Catalog=orders;User ID=app;Password=Sup3r$ecret!;",
        "Sup3r$ecret!",
        "[REDACTED_CONNECTION_STRING]",
        id="ado_net_password",
    ),
    pytest.param(
        "Driver={ODBC Driver 18 for SQL Server};Server=sql01;Uid=sa;Pwd=hunter2pass;Encrypt=yes;",
        "hunter2pass",
        "[REDACTED_CONNECTION_STRING]",
        id="odbc_pwd",
    ),
    pytest.param(
        "DefaultEndpointsProtocol=https;AccountName=contosostore;AccountKey=" + FAKE_AZURE_ACCOUNT_KEY
        + ";EndpointSuffix=core.windows.net",
        FAKE_AZURE_ACCOUNT_KEY,
        "[REDACTED_CONNECTION_STRING]",
        id="storage_account_key_pair",
    ),
    pytest.param(
        "connection refused: postgres://orders_app:pg-Pa55word@db.example.com:5432/orders",
        "pg-Pa55word",
        "[REDACTED_CONNECTION_STRING]",
        id="postgres_uri",
    ),
    pytest.param(
        "MongoServerError: bad auth : mongodb+srv://admin:m0ngoS3cret@cluster0.ab1cd.mongodb.net/test",
        "m0ngoS3cret",
        "[REDACTED_CONNECTION_STRING]",
        id="mongodb_uri",
    ),
    pytest.param(
        "jdbc:mysql://admin:jdbcS3cret@mysql.example.com:3306/shop",
        "jdbcS3cret",
        "[REDACTED_CONNECTION_STRING]",
        id="jdbc_uri",
    ),
    pytest.param('Server=sql01;Password="my s3cret pa55";', "pa55", "[REDACTED_CONNECTION_STRING]",
                 id="quoted_password_with_spaces"),
    pytest.param("Driver={ODBC Driver 18 for SQL Server};Pwd={p@ss;w0rd};", "w0rd", "[REDACTED_CONNECTION_STRING]",
                 id="odbc_braced_pwd"),
    pytest.param("DB_PWD=Hunter2x", "Hunter2x", "[REDACTED_CONNECTION_STRING]", id="env_pwd"),
    pytest.param("redis://:r3disPass@cache.example.com:6379", "r3disPass", "[REDACTED_CONNECTION_STRING]",
                 id="uri_password_without_user"),
    pytest.param("amqp://guest:pa/ss@rabbit.example.com:5672", "pa/ss", "[REDACTED_CONNECTION_STRING]",
                 id="uri_password_with_slash"),
    pytest.param(
        "> Authorization: Bearer 2YotnFZFEjr1zCsicMWpAAabc123xyz789",
        "2YotnFZFEjr1zCsicMWpAAabc123xyz789",
        "[REDACTED_BEARER_TOKEN]",
        id="authorization_bearer_header",
    ),
    pytest.param(
        "IDX10503: Signature validation failed. token: '" + FAKE_JWT + "'",
        FAKE_JWT,
        "[REDACTED_BEARER_TOKEN]",
        id="bare_jwt",
    ),
    pytest.param(
        "Using key " + FAKE_AZURE_ACCOUNT_KEY + " for storage account contosostore",
        FAKE_AZURE_ACCOUNT_KEY,
        "[REDACTED_CLOUD_KEY]",
        id="bare_azure_account_key",
    ),
    pytest.param(
        "GET https://contosostore.blob.core.windows.net/logs/app.log?sv=2022-11-02&sr=b&sig=pX3dQe5Zr%2Bk9Lm2Nq7Vt%3D 403",
        "pX3dQe5Zr%2Bk9Lm2Nq7Vt%3D",
        "[REDACTED_CLOUD_KEY]",
        id="sas_signature",
    ),
    pytest.param(
        "botocore.exceptions.ClientError: The AWS Access Key Id AKIAIOSFODNN7EXAMPLE does not exist",
        "AKIAIOSFODNN7EXAMPLE",
        "[REDACTED_CLOUD_KEY]",
        id="aws_access_key_id",
    ),
    pytest.param(
        "remote: Invalid credentials ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
        "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
        "[REDACTED_CLOUD_KEY]",
        id="github_token",
    ),
    pytest.param(
        "using github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz",
        "github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz",
        "[REDACTED_CLOUD_KEY]",
        id="github_fine_grained_token",
    ),
    pytest.param(
        "openai.AuthenticationError: Incorrect API key provided: sk-proj-a1B2c3D4e5F6g7H8i9J0",
        "sk-proj-a1B2c3D4e5F6g7H8i9J0",
        "[REDACTED_CLOUD_KEY]",
        id="sk_style_api_key",
    ),
    pytest.param(
        "  password: yamlS3cret",
        "yamlS3cret",
        "[REDACTED_SECRET_ASSIGNMENT]",
        id="yaml_password",
    ),
    pytest.param(
        "STRIPE_API_KEY=key_live_0123456789",
        "key_live_0123456789",
        "[REDACTED_SECRET_ASSIGNMENT]",
        id="env_api_key",
    ),
    pytest.param(
        "AADSTS7000215: Invalid client secret provided. client_secret=Xy7~Q8abcDEF.ghiJKL",
        "Xy7~Q8abcDEF.ghiJKL",
        "[REDACTED_SECRET_ASSIGNMENT]",
        id="client_secret",
    ),
    pytest.param(
        '{"refresh_token": "rt-0123456789abcdef", "expires_in": 3600}',
        "rt-0123456789abcdef",
        "[REDACTED_SECRET_ASSIGNMENT]",
        id="json_token",
    ),
    pytest.param("ClientSecret = 'abc d3f'", "d3f", "[REDACTED_SECRET_ASSIGNMENT]", id="quoted_secret_with_spaces"),
    pytest.param("export DB_PASS=s3cretvalue", "s3cretvalue", "[REDACTED_SECRET_ASSIGNMENT]", id="env_pass"),
    pytest.param("credential=Zx9-credvalue", "Zx9-credvalue", "[REDACTED_SECRET_ASSIGNMENT]", id="credential"),
    pytest.param(
        "Loaded key:\n" + PEM_BEGIN + "\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7\nYWJjZGVm\n" + PEM_END + "\ndone",
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7",
        "[REDACTED_PRIVATE_KEY]",
        id="pem_private_key",
    ),
    # A key under a secret-looking name must not lose only its first line to secret_assignment.
    pytest.param(
        '{"private_key": "' + RSA_PEM_BEGIN + "\\nMIIEowIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo\\n" + RSA_PEM_END + '\\n"}',
        "MIIEowIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo",
        "[REDACTED_PRIVATE_KEY]",
        id="json_escaped_rsa_private_key",
    ),
    pytest.param(
        "HttpRequestException: No such host is known. (build-agent-07.local:443)",
        "build-agent-07.local",
        "[REDACTED_INTERNAL_HOST]",
        id="local_host",
    ),
    pytest.param(
        "dial tcp: lookup payments.svc.internal: no such host",
        "payments.svc.internal",
        "[REDACTED_INTERNAL_HOST]",
        id="internal_host",
    ),
    pytest.param(
        "Failed to connect to jenkins.eu.corp port 8443",
        "jenkins.eu.corp",
        "[REDACTED_INTERNAL_HOST]",
        id="corp_host",
    ),
    pytest.param(
        "ECONNREFUSED nas.lan:2049",
        "nas.lan",
        "[REDACTED_INTERNAL_HOST]",
        id="lan_host",
    ),
    pytest.param("connect ETIMEDOUT 10.20.30.40:5432", "10.20.30.40", "[REDACTED_INTERNAL_HOST]", id="private_ip_10"),
    pytest.param("upstream 172.31.255.4 returned 502", "172.31.255.4", "[REDACTED_INTERNAL_HOST]", id="private_ip_172"),
    pytest.param("Ping 192.168.1.15 failed.", "192.168.1.15", "[REDACTED_INTERNAL_HOST]", id="private_ip_192"),
    pytest.param("Login failed for user 'jane.doe@contoso.com'.", "jane.doe@contoso.com", "[REDACTED_EMAIL]", id="email"),
    # An email on an internal domain is redacted whole, not left with its local part.
    pytest.param("notify ops-team@build01.corp", "ops-team", "[REDACTED_EMAIL]", id="email_on_internal_domain"),
]


@pytest.mark.parametrize(("log_line", "secret", "replacement"), SECRETS)
def test_every_secret_class_is_redacted(log_line: str, secret: str, replacement: str):
    redacted = redact(log_line)
    assert secret not in redacted
    assert replacement in redacted


def test_planted_secrets_in_one_log_are_all_redacted_and_the_diagnostics_kept():
    log = "\n".join([
        "fail: Microsoft.EntityFrameworkCore.Database.Connection[20004]",
        "      An error occurred using the connection to database 'orders' on server "
        "'tcp:contoso-sql.database.windows.net,1433'.",
        "      ConnectionString: Server=tcp:contoso-sql.database.windows.net,1433;Database=orders;"
        "User ID=app;Password=Pl4nted-Pa55!;",
        "      Authorization: Bearer " + FAKE_JWT,
        "      AWS key AKIAIOSFODNN7EXAMPLE, callback to 10.1.2.3, owner jane.doe@contoso.com",
        "Microsoft.Data.SqlClient.SqlException (0x80131904): Login failed for user 'app'.",
    ])

    redacted = redact(log)

    for secret in ["Pl4nted-Pa55!", FAKE_JWT, "AKIAIOSFODNN7EXAMPLE", "10.1.2.3", "jane.doe@contoso.com"]:
        assert secret not in redacted
    for diagnostic in [
        "Microsoft.Data.SqlClient.SqlException (0x80131904): Login failed for user 'app'.",
        "contoso-sql.database.windows.net",
        "Microsoft.EntityFrameworkCore.Database.Connection[20004]",
    ]:
        assert diagnostic in redacted


ORDINARY_LOG_TEXT = [
    # Public cloud hostnames
    "Failed to reach https://contoso-api.azurewebsites.net/api/orders (503 Service Unavailable)",
    "Request to https://contosostore.blob.core.windows.net/logs/app.log returned 404",
    "Server=tcp:contoso-sql.database.windows.net,1433 is not reachable",
    "https://myvault.vault.azure.net/secrets/db-password was not found",
    "Could not resolve host: my-bucket.s3.us-east-1.amazonaws.com",
    "push to registry.internal.cloudapp.net failed",
    "GET https://login.microsoftonline.com/common/oauth2/v2.0/token 400",
    # Ordinary error text that mentions secrets without containing one
    'PostgresError: password authentication failed for user "orders_app"',
    "IDX10223: Lifetime validation failed. The token is expired.",
    "System.UnauthorizedAccessException: Bearer token was not provided.",
    "WWW-Authenticate: Bearer error=\"invalid_token\"",
    "npm ERR! code E401 Unable to authenticate, your authentication token seems to be invalid.",
    # Version numbers and file names that look like IPs or internal hostnames
    "Could not load file or assembly 'System.Runtime, Version=10.0.0.0, Culture=neutral'.",
    "Could not load file or assembly 'Contoso.Billing, Version=10.1.2.3'.",
    "Microsoft.NET.Sdk 10.0.100 on Windows 10.0.19045",
    "Loaded settings from appsettings.local.json",
    "listening on http://127.0.0.1:5000 and http://localhost:5000",
    # Settings whose names only contain a secret word, and an ARN that names a secret without holding it
    "openai.BadRequestError: max_tokens: 200000 is too large",
    "usage: prompt_tokens=1234 completion_tokens=56",
    '{"token_type": "Bearer", "expires_in": 3599}',
    "access_token_url=https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "AccessDeniedException on arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/orders-db-AbCdEf",
    # .NET 10 runtime versions and PascalCase namespaces
    "Microsoft.AspNetCore.App 10.0.0.0 [/usr/share/dotnet/shared/Microsoft.AspNetCore.App]",
    "warn: Microsoft.EntityFrameworkCore.Internal[10403]",
    "at Contoso.Corp: unhandled exception",
    # A stack frame
    "   at Contoso.Orders.OrderRepository.GetAsync(Int32 id) in /src/Orders/OrderRepository.cs:line 42",
    "panic: runtime error: index out of range [5] with length 3",
]


@pytest.mark.parametrize("log_line", ORDINARY_LOG_TEXT)
def test_public_hostnames_and_ordinary_log_text_are_unchanged(log_line: str):
    assert redact(log_line) == log_line


def test_secrets_from_earlier_turns_are_redacted_again():
    """neuro-san sends the raw chat history with every new turn, so a secret pasted in an earlier turn must be
    redacted again before the next LLM call, not only the newest message."""
    conversation = redact_conversation([
        HumanMessage("Login failed. Server=sql01;Password=FirstTurnS3cret; owner jane.doe@contoso.com"),
        AIMessage("Which SQL Server version?"),
        HumanMessage("SQL Server 2022, host 10.4.5.6"),
    ])

    assert conversation[0].content == "Login failed. Server=sql01;[REDACTED_CONNECTION_STRING]; owner [REDACTED_EMAIL]"
    assert conversation[1].content == "Which SQL Server version?"
    assert conversation[2].content == "SQL Server 2022, host [REDACTED_INTERNAL_HOST]"
