"""Bound request bodies before JSON/form/multipart parsers allocate memory."""
from starlette.responses import JSONResponse

class RequestBodyLimit:
    def __init__(self,app,max_bytes=65536):self.app=app;self.max_bytes=max_bytes
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PUT','PATCH','DELETE'):
            return await self.app(scope,receive,send)
        events=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            size+=len(message.get('body',b''))
            if size>self.max_bytes:
                return await JSONResponse({'detail':'Nội dung yêu cầu vượt giới hạn 64 KB'},status_code=413)(scope,receive,send)
            events.append(message)
            if not message.get('more_body',False):break
        async def replay():return events.pop(0) if events else await receive()
        return await self.app(scope,replay,send)
