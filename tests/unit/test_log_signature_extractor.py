"""Error Signature extraction by the log_signature_extractor coded tool (spec seam 3). The input logs are already
redacted, as they are when the Coordinator calls the tool after its middleware has run."""

import asyncio
import json

from coded_tools.docs_qa.assistant.log_signature_extractor import LogSignatureExtractor


def extract(error_log: str) -> dict | str:
    return asyncio.run(LogSignatureExtractor().async_invoke({"error_log": error_log}, {}))


def test_dotnet_exception_reports_the_innermost_exception_and_its_frames():
    signature = extract("""fail: Microsoft.EntityFrameworkCore.Update[10000]
      An exception occurred in the database while saving changes for context type 'Orders.Api.OrdersContext'.
Unhandled exception. Microsoft.EntityFrameworkCore.DbUpdateException: An error occurred while saving the entity changes. See the inner exception for details.
 ---> Microsoft.Data.SqlClient.SqlException (0x80131904): Cannot insert the value NULL into column 'Name', table 'orders.dbo.Customers'; column does not allow nulls. INSERT fails.
   at Microsoft.Data.SqlClient.SqlConnection.OnError(SqlException exception, Boolean breakConnection, Action`1 wrapCloseInAction)
   at System.Runtime.CompilerServices.TaskAwaiter.HandleNonSuccessAndDebuggerNotification(Task task)
   at Microsoft.Data.SqlClient.SqlCommand.EndExecuteReaderAsync(IAsyncResult asyncResult)
   at Microsoft.EntityFrameworkCore.Update.ReaderModificationCommandBatch.ExecuteAsync(IRelationalConnection connection, CancellationToken cancellationToken)
ClientConnectionId:3f1c2a9e-5d0b-4c7e-9a43-1b2c3d4e5f60
Error Number:515,State:2,Class:16
   --- End of inner exception stack trace ---
   at Microsoft.EntityFrameworkCore.DbContext.SaveChangesAsync(Boolean acceptAllChangesOnSuccess, CancellationToken cancellationToken)
   at Orders.Api.CustomerService.CreateAsync(Customer customer) in /src/Orders.Api/CustomerService.cs:line 42
""")
    assert signature == {
        "error_type": "Microsoft.Data.SqlClient.SqlException",
        "error_code": "0x80131904",
        "message": "Cannot insert the value NULL into column 'Name', table 'orders.dbo.Customers'; column does not "
        "allow nulls. INSERT fails.",
        "library": "Microsoft.Data.SqlClient",
        "version": None,
        "frames": [
            "Microsoft.Data.SqlClient.SqlConnection.OnError(SqlException exception, Boolean breakConnection, "
            "Action`1 wrapCloseInAction)",
            "Microsoft.Data.SqlClient.SqlCommand.EndExecuteReaderAsync(IAsyncResult asyncResult)",
            "Microsoft.EntityFrameworkCore.Update.ReaderModificationCommandBatch.ExecuteAsync("
            "IRelationalConnection connection, CancellationToken cancellationToken)",
        ],
    }


def test_json_error_response_with_escaped_stack_trace_reports_the_innermost_exception_and_the_code():
    # A Dataverse Web API error as pasted in manual testing (issue 10): the exception chain and an escaped stack
    # trace sit in one JSON "message" string, and the HResult is in the "code" field.
    signature = extract(r""""code": "0x80048d19",
"message": "Error identified in Payload provided by the user for Entity :'', For more information on this error please follow this help link https://go.microsoft.com/fwlink/?linkid=2195293 ----> InnerException : Microsoft.OData.ODataException: Cannot convert the literal 'ead' to the expected type 'Edm.Int32'. ---> System.FormatException: Input string was not in a correct format.\r\n   at System.Number.StringToNumber(String str, NumberStyles options, NumberBuffer& number, NumberFormatInfo info, Boolean parseDecimal)\r\n   at System.Number.ParseInt32(String s, NumberStyles style, NumberFormatInfo info)\r\n   at System.String.System.IConvertible.ToInt32(IFormatProvider provider)\r\n   at System.Convert.ChangeType(Object value, Type conversionType, IFormatProvider provider)\r\n   at Microsoft.
""")
    assert signature == {
        "error_type": "System.FormatException",
        "error_code": "0x80048d19",
        "message": "Input string was not in a correct format.",
        "library": "System",
        "version": None,
        "frames": [
            "System.Number.StringToNumber(String str, NumberStyles options, NumberBuffer& number, "
            "NumberFormatInfo info, Boolean parseDecimal)",
            "System.Number.ParseInt32(String s, NumberStyles style, NumberFormatInfo info)",
            "System.String.System.IConvertible.ToInt32(IFormatProvider provider)",
        ],
    }


def test_dotnet_assembly_load_error_takes_library_and_version_from_the_assembly_name():
    signature = extract("""Unhandled exception. System.IO.FileNotFoundException: Could not load file or assembly 'Newtonsoft.Json, Version=13.0.0.0, Culture=neutral, PublicKeyToken=30ad4fe6b2a6aeed'. The system cannot find the file specified.
File name: 'Newtonsoft.Json, Version=13.0.0.0, Culture=neutral, PublicKeyToken=30ad4fe6b2a6aeed'
   at Orders.Worker.Program.Main(String[] args)
""")
    assert signature == {
        "error_type": "System.IO.FileNotFoundException",
        "error_code": None,
        "message": "Could not load file or assembly 'Newtonsoft.Json, Version=13.0.0.0, Culture=neutral, "
        "PublicKeyToken=30ad4fe6b2a6aeed'. The system cannot find the file specified.",
        "library": "Newtonsoft.Json",
        "version": "13.0.0.0",
        "frames": ["Orders.Worker.Program.Main(String[] args)"],
    }


def test_java_stack_trace_reports_the_root_cause_and_its_jar():
    signature = extract("""2024-05-01T10:15:30.123Z ERROR 1 --- [           main] o.s.boot.SpringApplication               : Application run failed

org.springframework.beans.factory.UnsatisfiedDependencyException: Error creating bean with name 'orderController': Unsatisfied dependency expressed through constructor parameter 0
	at org.springframework.beans.factory.support.ConstructorResolver.createArgumentArray(ConstructorResolver.java:795) ~[spring-beans-6.1.6.jar:6.1.6]
	at com.example.orders.OrdersApplication.main(OrdersApplication.java:10) ~[classes/:na]
Caused by: org.springframework.beans.factory.BeanCreationException: Error creating bean with name 'dataSource': Failed to instantiate [com.zaxxer.hikari.HikariDataSource]
	at org.springframework.beans.factory.support.AbstractBeanFactory.doGetBean(AbstractBeanFactory.java:326) ~[spring-beans-6.1.6.jar:6.1.6]
	... 20 common frames omitted
Caused by: org.springframework.boot.autoconfigure.jdbc.DataSourceProperties$DataSourceBeanCreationException: Failed to determine a suitable driver class
	at java.base/jdk.internal.reflect.DirectMethodHandleAccessor.invoke(DirectMethodHandleAccessor.java:103) ~[na:na]
	at org.springframework.boot.autoconfigure.jdbc.DataSourceProperties.determineDriverClassName(DataSourceProperties.java:186) ~[spring-boot-autoconfigure-3.2.5.jar:3.2.5]
	at org.springframework.boot.autoconfigure.jdbc.DataSourceConfiguration.createDataSource(DataSourceConfiguration.java:59) ~[spring-boot-autoconfigure-3.2.5.jar:3.2.5]
	... 30 common frames omitted
""")
    assert signature == {
        "error_type": "org.springframework.boot.autoconfigure.jdbc.DataSourceProperties$DataSourceBeanCreationException",
        "error_code": None,
        "message": "Failed to determine a suitable driver class",
        "library": "spring-boot-autoconfigure",
        "version": "3.2.5",
        "frames": [
            "org.springframework.boot.autoconfigure.jdbc.DataSourceProperties.determineDriverClassName("
            "DataSourceProperties.java:186) ~[spring-boot-autoconfigure-3.2.5.jar:3.2.5]",
            "org.springframework.boot.autoconfigure.jdbc.DataSourceConfiguration.createDataSource("
            "DataSourceConfiguration.java:59) ~[spring-boot-autoconfigure-3.2.5.jar:3.2.5]",
        ],
    }


def test_java_exception_without_a_jar_falls_back_to_the_exception_package():
    signature = extract("""Exception in thread "main" java.lang.NullPointerException
	at com.example.orders.OrderService.total(OrderService.java:31)
	at com.example.orders.Main.main(Main.java:12)
""")
    assert signature == {
        "error_type": "java.lang.NullPointerException",
        "error_code": None,
        "message": "",
        "library": "java.lang",
        "version": None,
        "frames": [
            "com.example.orders.OrderService.total(OrderService.java:31)",
            "com.example.orders.Main.main(Main.java:12)",
        ],
    }


def test_go_panic_takes_the_module_and_version_from_the_frames():
    signature = extract("""panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x6f1b2a]

goroutine 34 [running]:
github.com/gin-gonic/gin.(*Context).JSON(...)
	/go/pkg/mod/github.com/gin-gonic/gin@v1.9.1/context.go:1056
example.com/orders/handlers.GetOrder(0xc0001a2000)
	/app/handlers/orders.go:27 +0x8a
github.com/gin-gonic/gin.(*Context).Next(...)
	/go/pkg/mod/github.com/gin-gonic/gin@v1.9.1/context.go:174
net/http.(*conn).serve(0xc000218000, {0x8b3f50, 0xc00020a0f0})
	/usr/local/go/src/net/http/server.go:2009 +0x8f5
created by net/http.(*Server).Serve in goroutine 1
	/usr/local/go/src/net/http/server.go:3086 +0x5cb
""")
    assert signature == {
        "error_type": "panic",
        "error_code": "SIGSEGV",
        "message": "runtime error: invalid memory address or nil pointer dereference",
        "library": "github.com/gin-gonic/gin",
        "version": "v1.9.1",
        "frames": [
            "github.com/gin-gonic/gin.(*Context).JSON(...) /go/pkg/mod/github.com/gin-gonic/gin@v1.9.1/context.go:1056",
            "example.com/orders/handlers.GetOrder(0xc0001a2000) /app/handlers/orders.go:27 +0x8a",
            "github.com/gin-gonic/gin.(*Context).Next(...) /go/pkg/mod/github.com/gin-gonic/gin@v1.9.1/context.go:174",
        ],
    }


def test_go_panic_in_plain_go_code_names_go_and_skips_runtime_frames():
    signature = extract("""panic: assignment to entry in nil map

goroutine 1 [running]:
runtime.mapassign_faststr(0x4b2a40, 0x0, {0x4c1b2e, 0x5})
	/usr/local/go/src/runtime/map_faststr.go:205 +0x3b7
main.main()
	/app/main.go:8 +0x45
exit status 2
""")
    assert signature == {
        "error_type": "panic",
        "error_code": None,
        "message": "assignment to entry in nil map",
        "library": "Go",
        "version": None,
        "frames": ["main.main() /app/main.go:8 +0x45"],
    }


def test_recovered_go_panic_keeps_the_repeated_panic_line_out_of_the_frames():
    signature = extract("""panic: sql: database is closed [recovered]
	panic: sql: database is closed

goroutine 1 [running]:
main.main()
	/app/main.go:8 +0x45
""")
    assert signature == {
        "error_type": "panic",
        "error_code": None,
        "message": "sql: database is closed [recovered]",
        "library": "Go",
        "version": None,
        "frames": ["main.main() /app/main.go:8 +0x45"],
    }


def test_node_error_names_the_package_from_node_modules_and_skips_internal_frames():
    signature = extract("""/app/node_modules/express/lib/router/index.js:646
            return fn.apply(this, arguments);
TypeError: Cannot read properties of undefined (reading 'id')
    at getOrder (/app/src/routes/orders.js:14:32)
    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
    at next (/app/node_modules/express/lib/router/route.js:149:13)

Node.js v20.11.1
""")
    assert signature == {
        "error_type": "TypeError",
        "error_code": None,
        "message": "Cannot read properties of undefined (reading 'id')",
        "library": "express",
        "version": None,
        "frames": [
            "getOrder (/app/src/routes/orders.js:14:32)",
            "Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)",
            "next (/app/node_modules/express/lib/router/route.js:149:13)",
        ],
    }


def test_node_error_with_only_internal_frames_names_node_and_its_version():
    signature = extract("""node:internal/modules/cjs/loader:1147
  throw err;
  ^

Error: Cannot find module 'express'
Require stack:
- /app/server.js
    at Module._resolveFilename (node:internal/modules/cjs/loader:1144:15)
    at Module._load (node:internal/modules/cjs/loader:985:27) {
  code: 'MODULE_NOT_FOUND',
  requireStack: [ '/app/server.js' ]
}

Node.js v20.11.1
""")
    assert signature == {
        "error_type": "Error",
        "error_code": "MODULE_NOT_FOUND",
        "message": "Cannot find module 'express'",
        "library": "Node.js",
        "version": "20.11.1",
        "frames": [],
    }


def test_node_error_names_the_package_in_its_message_and_drops_the_object_brace():
    signature = extract("""node:internal/modules/cjs/loader:1080
Error [ERR_REQUIRE_ESM]: require() of ES Module /app/node_modules/node-fetch/src/index.js from /app/index.js not supported.
    at Object.<anonymous> (/app/index.js:1:15) {
  code: 'ERR_REQUIRE_ESM'
}

Node.js v18.17.0
""")
    assert signature == {
        "error_type": "Error",
        "error_code": "ERR_REQUIRE_ESM",
        "message": "require() of ES Module /app/node_modules/node-fetch/src/index.js from /app/index.js not "
        "supported.",
        "library": "node-fetch",
        "version": None,
        "frames": ["Object.<anonymous> (/app/index.js:1:15)"],
    }


def test_node_error_under_npm_start_reports_the_node_error_not_the_npm_wrapper():
    # npm names the user's own package (orders-web@0.1.0), which is not the library that failed.
    signature = extract("""/app/server.js:3
const total = order.id;
TypeError: Cannot read properties of undefined (reading 'id')
    at Object.<anonymous> (/app/server.js:3:21)
    at Module._compile (node:internal/modules/cjs/loader:1256:14)
npm ERR! code ELIFECYCLE
npm ERR! errno 1
npm ERR! orders-web@0.1.0 start: `node server.js`
npm ERR! Exit status 1
""")
    assert signature == {
        "error_type": "TypeError",
        "error_code": None,
        "message": "Cannot read properties of undefined (reading 'id')",
        "library": None,
        "version": None,
        "frames": ["Object.<anonymous> (/app/server.js:3:21)"],
    }


def test_npm_error_reports_the_code_and_the_package_it_found():
    signature = extract("""npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
npm ERR!
npm ERR! While resolving: orders-web@0.1.0
npm ERR! Found: react@18.2.0
npm ERR! node_modules/react
npm ERR!   react@"^18.2.0" from the root project
npm ERR!
npm ERR! Could not resolve dependency:
npm ERR! peer react@"^16.8.0 || ^17.0.0" from react-beautiful-dnd@13.1.1
npm ERR!
npm ERR! Fix the upstream dependency conflict, or retry
npm ERR! this command with --force or --legacy-peer-deps
""")
    assert signature == {
        "error_type": None,
        "error_code": "ERESOLVE",
        "message": "ERESOLVE unable to resolve dependency tree",
        "library": "react",
        "version": "18.2.0",
        "frames": [],
    }


def test_npm_10_error_prefix_is_recognized():
    signature = extract("""npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/left-padd - Not found
npm error 404  'left-padd@1.0.0' is not in this registry.
""")
    assert signature == {
        "error_type": None,
        "error_code": "E404",
        "message": "404 Not Found - GET https://registry.npmjs.org/left-padd - Not found",
        "library": "left-padd",
        "version": "1.0.0",
        "frames": [],
    }


def test_csharp_compiler_error_reports_the_code_location_and_target_framework():
    signature = extract("""  Determining projects to restore...
  All projects are up-to-date for restore.
/src/Orders.Api/Program.cs(12,17): error CS0246: The type or namespace name 'OrdersContext' could not be found (are you missing a using directive or an assembly reference?) [/src/Orders.Api/Orders.Api.csproj::TargetFramework=net8.0]

Build FAILED.
""")
    assert signature == {
        "error_type": None,
        "error_code": "CS0246",
        "message": "The type or namespace name 'OrdersContext' could not be found (are you missing a using "
        "directive or an assembly reference?)",
        "library": ".NET",
        "version": "net8.0",
        "frames": ["/src/Orders.Api/Program.cs(12,17)"],
    }


def test_typescript_compiler_error_reports_the_code_and_location():
    signature = extract("""src/App.tsx:5:10 - error TS2305: Module '"react-router-dom"' has no exported member 'Switch'.

5 import { Switch, Route } from "react-router-dom";
           ~~~~~~

Found 1 error in src/App.tsx:5
""")
    assert signature == {
        "error_type": None,
        "error_code": "TS2305",
        "message": "Module '\"react-router-dom\"' has no exported member 'Switch'.",
        "library": "TypeScript",
        "version": None,
        "frames": ["src/App.tsx:5:10"],
    }


def test_redacted_log_lines_outside_the_error_stay_out_of_the_signature():
    # The planted-secret fixture's log after redaction: only the exception reaches the signature.
    signature = extract("""fail: Microsoft.EntityFrameworkCore.Database.Connection[20004]
      An error occurred using the connection to database 'orders' on server 'tcp:contoso-sql.database.windows.net,1433'.
      ConnectionStrings__Orders=Server=tcp:contoso-sql.database.windows.net,1433;Database=orders;User ID=app;[REDACTED_CONNECTION_STRING];
      Outgoing request header: Authorization: [REDACTED_BEARER_TOKEN]
Microsoft.Data.SqlClient.SqlException (0x80131904): Login failed for user 'app'.
""")
    assert signature == {
        "error_type": "Microsoft.Data.SqlClient.SqlException",
        "error_code": "0x80131904",
        "message": "Login failed for user 'app'.",
        "library": "Microsoft.Data.SqlClient",
        "version": None,
        "frames": [],
    }
    assert "REDACTED" not in json.dumps(signature)


def test_unrecognized_log_keeps_only_its_first_error_line():
    signature = extract("""Starting orders worker
2024-05-01 10:00:00 connection to broker failed: connection refused
retrying in 5s
""")
    assert signature == {
        "error_type": None,
        "error_code": None,
        "message": "2024-05-01 10:00:00 connection to broker failed: connection refused",
        "library": None,
        "version": None,
        "frames": [],
    }


def test_long_message_is_cut_to_keep_the_signature_short():
    signature = extract("System.InvalidOperationException: " + "x" * 1000)
    assert isinstance(signature, dict)
    assert len(signature["message"]) == 300
    assert signature["message"].endswith("...")


def test_empty_log_returns_an_error_the_coordinator_can_act_on():
    assert extract("   \n") == "Error: error_log is empty. Pass the Error Log from the user's message."
