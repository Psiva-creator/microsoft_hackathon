from app.core.fingerprint import fingerprints, parse_stack_trace


def test_python_stack_trace_fingerprint_identical():
    trace1 = (
        "Traceback (most recent call last):\n"
        '  File "/usr/local/lib/python3.12/site-packages/urllib3/connectionpool.py", line 400, in urlopen\n'
        "    body = response.read()\n"
        '  File "/app/services/checkout/client.py", line 42, in call_remote\n'
        "    return session.get(url)\n"
        '  File "/app/services/checkout/handler.py", line 120, in handle_request\n'
        '    call_remote(req_id="4b46c646-7788-46cb-84aa-fbb87d8bc291")\n'
        "ConnectionError: connection timed out\n"
    )
    trace2 = (
        "Traceback (most recent call last):\n"
        '  File "/usr/local/lib/python3.12/site-packages/urllib3/connectionpool.py", line 550, in urlopen\n'
        "    body = response.read()\n"
        '  File "/app/services/checkout/client.py", line 98, in call_remote\n'
        "    return session.get(url)\n"
        '  File "/app/services/checkout/handler.py", line 245, in handle_request\n'
        '    call_remote(req_id="99aa88bb-1122-3344-5566-778899aabbcc")\n'
        "ConnectionError: connection timed out\n"
    )
    fps1 = fingerprints(trace1)
    fps2 = fingerprints(trace2)
    # The stack fingerprint (index 0) must be identical despite line numbers and UUIDs
    assert fps1[0] == fps2[0]


def test_different_top_frames_produce_different_fingerprints():
    trace1 = (
        "Traceback (most recent call last):\n"
        '  File "/app/services/checkout/handler.py", line 10, in handle_payment\n'
        "    process()\n"
        "RuntimeError: operation failed\n"
    )
    trace2 = (
        "Traceback (most recent call last):\n"
        '  File "/app/services/inventory/stock.py", line 25, in reserve_stock\n'
        "    reserve()\n"
        "RuntimeError: operation failed\n"
    )
    fps1 = fingerprints(trace1)
    fps2 = fingerprints(trace2)
    assert fps1[0] != fps2[0]


def test_java_stack_trace_parsing():
    trace = (
        "com.zaxxer.hikari.pool.HikariPool$PoolInitializationException: Exception during pool initialization\n"
        "    at com.zaxxer.hikari.pool.HikariPool.checkPoolState(HikariPool.java:518)\n"
        "    at com.acme.order.service.OrderRepository.findOrder(OrderRepository.java:84)\n"
    )
    frames = parse_stack_trace(trace)
    assert len(frames) == 2
    assert frames[1].is_app is True
    assert "findOrder" in frames[1].function
