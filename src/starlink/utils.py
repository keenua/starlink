from os import path
from httpx import Response

def config_path(file_name: str):
    return path.join(path.dirname(__file__), f"config/{file_name}")

def setup():
    from dotenv import load_dotenv
    load_dotenv()

    import logging
    logging.basicConfig(filename='log.log', encoding='utf-8', level=logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)

async def response_to_str_single(response: Response) -> str:
    req_prefix = "< "
    res_prefix = "> "
    request = response.request
    output = []

    output.append(f"{req_prefix}{request.method} {request.url}")

    for name, value in request.headers.items():
        output.append(f"{req_prefix}{name}: {value}")

    output.append(req_prefix)

    await request.aread()
    
    content = request.content.decode("utf-8")
    output.append(f"{req_prefix}{content}")

    output.append("")

    output.append(
        f"{res_prefix} {response.status_code} {response.reason_phrase}"
    )

    for name, value in response.headers.items():
        output.append(f"{res_prefix}{name}: {value}")

    output.append(res_prefix)

    await response.aread()

    output.append(f"{res_prefix}{response.text}")

    return "\n".join(output)

async def response_to_str(response: Response) -> str:
    data = []

    history = list(response.history[:])
    history.append(response)

    for response in history:
        response_str = await response_to_str_single(response)
        data.append(response_str)

    return "\n".join(data)