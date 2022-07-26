import socket
import struct
import io
import json
#import logging
import sys


class Message:

    @staticmethod
    def _json_decode(raw_data : bytes, encoding : str):
        text_io_wrapper = io.TextIOWrapper(
            io.BytesIO(raw_data), encoding=encoding, newline="")
        object = json.load(text_io_wrapper)
        text_io_wrapper.close()
        return object

    @staticmethod
    def _json_encode(object, encoding: str) -> bytes:
        return json.dumps(obj=object, ensure_ascii=False).encode(encoding)


    def __init__(self, socket: socket.socket, package_size: int, version_name):
        self.version_name = version_name
        self.socket = socket
        self.package_size = package_size
        self.reset_reading_state()


    def reset_reading_state(self) -> None:
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self._send_buffer = b""
        self._receive_buffer = b""


    def get_field_values(self) -> dict:
        self.write_request('get_field_values')
        self.read_request()
        field_value_dictionary = self.request
        self.reset_reading_state()
        return field_value_dictionary

    def change_room_status(self, indices : list) -> str:
        self.write_request('post_new_state', indices)
        self.read_request()
        request_result = self.request.get('result')
        request_code_value = self.request.get('code_value')
        self.reset_reading_state()
        return (request_result, request_code_value)

# Message processing section

    def process_protoheader(self) -> None:
        header_length = 2  # in bytes
        if len(self._receive_buffer) >= header_length:
            self._jsonheader_len = struct.unpack(
                ">H", self._receive_buffer[:header_length])[0]
            self._receive_buffer = self._receive_buffer[header_length:]

    def process_jsonheader(self) -> None:
        header_length = self._jsonheader_len
        if len(self._receive_buffer) >= header_length:
            self.jsonheader = Message._json_decode(
                self._receive_buffer[:header_length], "utf-8")
            self._receive_buffer = self._receive_buffer[header_length:]

            for necessary_element in ('byteorder', 'content-length', 'content-type', 'content-encoding'):
                if necessary_element not in self.jsonheader:
                    raise ValueError(
                        f"Missing required header element: '{necessary_element}'")

    def process_request(self) -> None:
        content_length = self.jsonheader['content-length']
        if not len(self._receive_buffer) >= content_length:
            return  # if the message hasn't yet accumulated, we wait until it does
        data = self._receive_buffer[:content_length]
        self._receive_buffer = self._receive_buffer[content_length:]
        encoding = self.jsonheader['content-encoding']
        self.request = self._json_decode(data, encoding)
        #logging.debug(f"Received request {self.request} from {self.address}")
# End of message processing section

# Message assembly section
    def compose_request(self, request_action : str, request_data=[] ) -> dict:
        if request_action == 'get_field_values':
            content = {
                'action': 'get_field_values',
                'version': self.version_name
            }
        elif request_action == 'post_new_state':
            if request_data == []:
                raise ValueError(
                    'While composing request, incorrect request_data was provided.')
            content = {
                'action': 'post_new_state',
                'data': {
                    'room_index': request_data[0],
                    'doctor_index': request_data[1],
                    'study_index': request_data[2],
                    'state_index': request_data[3]
                }
            }
        if content:
            content_encoding = 'utf-8'
            response = {
                'content_bytes': Message._json_encode(content, content_encoding),
                'content_type': 'text/json',
                'content_encoding': content_encoding
            }
            return response
        raise ValueError(
            'While composing request, incorrect request_action was provided.')

    def create_request(self, content_bytes : bytes, content_type : str, content_encoding : str):
        content_length = len(content_bytes)
        jsonheader = {
            'byteorder': sys.byteorder,
            'content-type': content_type,
            'content-encoding': content_encoding,
            'content-length': content_length
        }
        jsonheader_bytes = Message._json_encode(jsonheader, 'utf-8')
        message_header = struct.pack('>H', len(jsonheader_bytes))
        return message_header + jsonheader_bytes + content_bytes
# End of message assembly section
# Socket actions section

    def read_request(self) -> dict:
        def read_from_socket_once():
            try:
                data = self.socket.recv(self.package_size)
            except BlockingIOError:
                return
            else:
                if data:
                    self._receive_buffer += data
                else:
                    raise RuntimeError('Peer closed')
        while self.request is None:
            read_from_socket_once()

            if self._jsonheader_len is None:
                self.process_protoheader()

            if self._jsonheader_len is not None:
                if self.jsonheader is None:
                    self.process_jsonheader()

            if self.jsonheader is not None:
                if self.request is None:
                    self.process_request()
        return self.request

    def write_request(self, request_action : str, request_data=[]) -> None:
        request_body = self.compose_request(request_action, request_data)
        self._send_buffer += self.create_request(**request_body)

        while len(self._send_buffer) > 0:
            try:
                sent = self.socket.send(self._send_buffer)
            except BlockingIOError:
                continue
            else:
                self._send_buffer = self._send_buffer[sent:]
# End of socket actions section
