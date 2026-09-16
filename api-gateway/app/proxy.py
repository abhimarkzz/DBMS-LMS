import httpx
from fastapi import Request, HTTPException, status
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

async def forward_request(request: Request, target_url: str, path: str):
    url = f"{target_url}/{path}"
    
    headers = dict(request.headers)
    headers.pop("host", None)
    
    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    
    try:
        req = client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            content=request.stream()
        )
        
        response = await client.send(req, stream=True)
        
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=dict(response.headers),
            background=client.aclose
        )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to downstream service at {url}: {e}")
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Downstream service is unreachable"
        )
    except httpx.ReadTimeout as e:
        logger.error(f"Timeout while reading from downstream service at {url}: {e}")
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Downstream service timed out"
        )
    except Exception as e:
        logger.error(f"Unexpected error forwarding to {url}: {e}")
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Gateway Error"
        )
