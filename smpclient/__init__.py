"""Simple Management Protocol (SMP) Client."""


from pydantic import ValidationError
from smp import header as smpheader
from smp import packet as smppacket

from smpclient.generics import SMPRequest, TEr0, TEr1, TErr, TRep, flatten_error
from smpclient.transport import SMPTransport


class SMPClient:
    def __init__(self, transport: SMPTransport, address: str):
        self._transport = transport
        self._address = address

    async def connect(self) -> None:
        await self._transport.connect(self._address)

    async def request(self, request: SMPRequest[TRep, TEr0, TEr1, TErr]) -> TRep | TErr:
        for packet in smppacket.encode(request.BYTES):
            await self._transport.send(packet)

        decoder = smppacket.decode()
        next(decoder)

        while True:
            try:
                b = await self._transport.readuntil()
                decoder.send(b)
            except StopIteration as e:
                frame = e.value
                break

        header = smpheader.Header.loads(frame[: smpheader.Header.SIZE])

        if header.sequence != request.header.sequence:  # type: ignore
            raise Exception("Bad sequence")

        try:
            return request.Response.loads(frame)  # type: ignore
        except ValidationError:
            return flatten_error(  # type: ignore
                request.ErrorV0.loads(frame)
                if header.version == smpheader.Version.V0
                else request.ErrorV1.loads(frame)
            )