"""Egress proxy: the only way out of the jail network.

Two clients, two rules, decided by the caller's IP (resolved from the compose service name):
- installer: may CONNECT to the package registries in INSTALL_HOSTS, and nothing else.
- agent runs (one throwaway container each) and the scoring sandbox: may CONNECT nowhere. It may only POST /llm/<path>, which is forwarded
  to https://openrouter.ai/api/<path> with the API key added here. The sandbox never holds the key.
Anything else is refused. Every decision is appended to /logs/egress.jsonl, so each run's
evidence block can show exactly what left the box.
"""
import asyncio
import http.client
import json
import os
import socket
import ssl
import time

INSTALL_HOSTS = {"registry.npmjs.org", "nodejs.org", "codeload.github.com",
                 # ripgrep and similar postinstalls fetch release binaries; installer only, never the agent
                 "github.com", "api.github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
OR_KEY = os.environ["OPENROUTER_API_KEY"]
LOG = open("/logs/egress.jsonl", "a", buffering=1)


def log(**kv):
    LOG.write(json.dumps({"ts": round(time.time(), 3), **kv}) + "\n")


def client_of(ip):
    # Agent runs are throwaway containers with no service name, so anything that is not the
    # installer or the scoring sandbox is an agent.
    for name in ("installer", "sandbox"):
        try:
            if ip in {a[4][0] for a in socket.getaddrinfo(name, None)}:
                return name
        except socket.gaierror:
            pass
    return "agent"


async def pipe(r, w):
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except ConnectionError:
        pass
    finally:
        w.close()


def forward(path, body):
    conn = http.client.HTTPSConnection("openrouter.ai", timeout=600, context=ssl.create_default_context())
    conn.request("POST", path, body, {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                                      "X-Title": "n8n-agent-bench"})
    r = conn.getresponse()
    return r.status, r.read()


async def deny(writer, **kv):
    log(allowed=False, **kv)
    writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
    await writer.drain()
    writer.close()


async def handle(reader, writer):
    client = client_of(writer.get_extra_info("peername")[0])
    head = await reader.readuntil(b"\r\n\r\n")
    line, *hdrs = head.decode("latin-1").split("\r\n")
    method, target, _ = line.split(" ", 2)

    if method == "CONNECT":
        host, _, port = target.rpartition(":")
        if client != "installer" or host not in INSTALL_HOSTS or port != "443":
            return await deny(writer, client=client, kind="connect", host=host)
        log(client=client, kind="connect", host=host, allowed=True)
        ur, uw = await asyncio.open_connection(host, 443)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(pipe(reader, uw), pipe(ur, writer))
        return

    if method == "POST" and target.startswith("/llm/") and client in ("agent", "sandbox"):
        length = next(int(h.split(":", 1)[1]) for h in hdrs if h.lower().startswith("content-length"))
        body = await reader.readexactly(length)
        path = "/api/" + target[len("/llm/"):]
        status, data = await asyncio.to_thread(forward, path, body)
        run_id = next((h.split(":", 1)[1].strip() for h in hdrs if h.lower().startswith("x-bench-run")), None)
        log(client=client, kind="llm", run=run_id, path=path, status=status,
            req_bytes=len(body), resp_bytes=len(data), allowed=True)
        writer.write(f"HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\n"
                     f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data)
        await writer.drain()
        writer.close()
        return

    await deny(writer, client=client, kind="http", method=method, target=target[:200])


async def main():
    srv = await asyncio.start_server(handle, "0.0.0.0", 8080)
    async with srv:
        await srv.serve_forever()


asyncio.run(main())
