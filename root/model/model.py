import json
import base64
from io import BytesIO
from openai import OpenAI
from config import Config
from datetime import datetime, timedelta
from root.model.tools import ModelTools
from typing import Callable


class Model:
    __slots__ = (
        "client",
        "model",
        "prompts",
        "tools",
        "tools_to_functions",
        "_current_thread",
        "tts_voice",
        "tts_speed",
    )

    def __init__(self, savior_id: str, amulet_tools: dict[str, Callable]):
        client = OpenAI()
        self.client = client
        model_tools = ModelTools(
            embeddings_generator=self.generate_embeddings, savior_id=savior_id
        )
        self.tools, tools_to_functions, self.prompts = model_tools.helpers
        get_amulet_view = amulet_tools.pop("get_view")
        vision_model = VisionModel(
            client=client, get_image = get_amulet_view, prompt=self.prompts["vision"]
        )
        self.tools_to_functions = {
            **tools_to_functions, 
            **amulet_tools,
            "describe_user_view": vision_model.describe_user_view,
        }
        self.tts_voice = model_tools.savior["tts_voice"]
        config = Config()
        self.tts_speeed = config.tts_speed
        self.chat_temperature = config.chat_temperature
        self.vision_temperature = config.vision_temperature
        self.max_vision_tokens = config.max_vision_tokens
        self.audio_input_file = config.audio_input_file
        self.audio_output_file = config.audio_output_file
        self._current_thread = {"last_interaction": datetime.now(), "thread": []}

    @property
    def current_thread(self) -> list:
        """Keeps track of conversation history and resets it every
        10 minutes of inactivity
        """
        now = datetime.now()
        last_interaction = self._current_thread["last_interaction"]
        if now - last_interaction > timedelta(minutes=10):
            thread = []
            self._current_thread["thread"] = thread
            return thread
        else:
            return self._current_thread["thread"]

    @current_thread.setter
    def current_thread(self, messages: list) -> None:
        self._current_thread = {"last_interaction": datetime.now(), "thread": messages}


    # def audio_to_text(self, audio_file: str) -> str:
    #     """Turns audio bytes into text for a chat completion"""
    #     with open(audio_file, "rb") as audio_bytes:
    #         text = self.client.audio.transcriptions.create(
    #             model="whisper-1", file=audio_bytes, prompt=self.prompts["audio"]
    #         )
    #     print(text.text)
    #     return text.text

    def text_to_audio(self, text: str) -> str:
        """Writes the given text to an audio file for the amulet to handle"""

        output_filepath = self.audio_output_file

        audio = self.client.audio.speech.create(
            input=text, model="tts-1", voice=self.tts_voice, speed=1.05
        )

        audio.stream_to_file(output_filepath)
        return output_filepath

    def moderate(self, text: str) -> bool:
        """Moderates the given text"""
        response = self.client.moderations.create(input=text)

        return response.result[0].flagged

    def format_inputs(self, content: str, prompt: str | None) -> list:
        """Properly formats a query for a completions model

        Args:
            content: The text to feed to the model
            prompt (optional): a prompt to prepend to the messages to return
        """

        # TODO: IF WE DECIDE TO DO VARIOUS PROMPTS UNCOMMENT THIS
        current_query = {"role": "user", "content": content}
        # if prompt and not self.current_thread:
        #     prompt = [prompt] if isinstance(prompt, dict) else prompt
        #     if isinstance(prompt, list):
        #         prompt.append(current_query)
        #     else:
        #         messages = [
        #         {"role": "system", "content": prompt},
        #         {"role": "user", "content": content}
        #       ]
        # else:
        #     messages = [current_query]
        messages = (
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ]
            if prompt
            else self.current_thread + [current_query]
        )
        return messages

    def generate_embeddings(self, text: str) -> list:
        """Returns a list of text embeddings"""
        response = self.client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )

        return response.data[0].embedding

    def encode_image(self, image_file: str) -> str:
        """Encodes an image file to base64 format for vision model input"""
        with open(image_file, "rb") as im:
            b64_image = base64.b64encode(im.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_image}"

    def get_vision_completion(
        self, messages: list, image_file: str, tools: list = None
    ) -> dict:
        # TODO: COME BACK TO WHATS WRITTEN BELOW
        """Implements a call to gpt with vision

        NOTE AND COME BACK TO: the previous calls
        were from the text only model which requested an image, and in the function response
        the get_current_view tool only returns an image file string, we add the image details
        the next message instead of the function response, not 100% sure if this is correct

        Args:
            messages: the thread to continue
            image_file: image_file to encode and append to list of passed messages

        Returns: a chat completions response
        """
        encoded_image = self.encode_image(image_file)
        image_query = {
            "role": "user",
            "content": [
                {"type": "text", "text": None},
                {
                    "type": "image_url",
                    "image_url": {"url": encoded_image, "detail": "low"},
                    # detail low, the Amulet won't capture big pictures
                },
            ],
        }
        messages.append(image_query)
        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            tools=tools,
            # temperature=self.vision_temperature
            # max_tokens=self.vision_max_tokens
        )        
        return response

    def get_chat_completion(self, messages: list[dict], tools: list = None) -> dict:
        """Returns a chat completion response from a text-only model"""

        res = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=tools,
            temperature=self.chat_temperature
        )

        return res

    def call_tools(self, tool_calls: list, messages: list) -> list:
        """Loops through a given list of function call requests from a model
        and then feeds the response back to it for the final output

        Args:
            tool_calls: the tool calls requested by the model
            messages: the current interaction / thread

        Returns:
            the new thread of messages - including the function call(s), result(s)

        """
        tools_to_functions = self.tools_to_functions
        requested_user_view = []
        for tool in tool_calls:
            try:
                function_name = tool.function.name
                function_call = tools_to_functions[function_name]
                arguments = json.loads(tool.function.arguments)
                function_response = function_call(**arguments)
                requested_user_view.append(function_name == "describe_user_view")
            except Exception as e:
                function_response = f"Error: {repr(e)}. Ask the user for more information before continuing."
            messages.append(
                {
                    "tool_call_id": tool.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        return messages, any(requested_user_view)

    def __call__(self, audio_input: BytesIO) -> str:
        """End to end function that handles an input audio file of
        a user query and returns another audio file

        Args:
            audio_bytes: The recorded bytes of the user's query

        Returns: An audio file location reference containing the tts response
        """
        print("whisper starting")
        text = self.audio_to_text(audio_buffer=audio_input)
        print("whisper done")
        # TODO: check what happens when whisper is given blank audio and if we can use control flow before or after an input to it
        prompt = self.prompts["chat"] if not self.current_thread else None
        messages = self.format_inputs(content=text, prompt=prompt)
        print("chat starting")
        response = self.get_chat_completion(messages=messages, tools=self.tools)
        print("chat done")
        response_message = response.choices[0].message

        is_flagged = self.moderate(messages)
        if is_flagged:
            raise Exception("The query was flagged by moderations")
        # create ref instead of rekeying in the loop
        tool_calls, call_tools = response_message.tool_calls, self.call_tools
        while tool_calls:
            print("while tool calls")
            messages.append(response_message)
            messages, requested_user_view = call_tools(
                tool_calls=tool_calls, messages=messages
            )
            print(messages, "from after tool calls")
            print("REQUESTED USER VIEW SHOULD BE FALSE: ", requested_user_view)
            print("chat 2 starting")
            response = self.get_chat_completion(
                messages=messages, tools=self.tools if requested_user_view else None
            )  # can add tools here too
            print("chat 2 done")
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
        messages.append(response_message)
        self.current_thread = messages
        if (res := response_message.content): 
            print("now tts")
            return self.text_to_audio(res)


class VisionModel:
    __slots__  = ("client", "get_image", "prompt")
    
    def __init__(self, client: OpenAI, get_image: Callable, prompt: str): 
        self.client = client
        self.prompt = prompt
        self.get_amulet_view = get_image
        
    def encode_image(self, image_buffer: BytesIO) -> str:
        """Encodes an image to base64 format for vision model input"""
        b64_image = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
        encoded_image = f"data:image/jpeg;base64,{b64_image}"
        image_buffer.close()
        return encoded_image
    
    def format_vision_inputs(self, encoded_image: str) -> list:
        vision_prompt = {"role": "system", "content": self.prompt}
        messages = [
            vision_prompt,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": None},
                    {
                        "type": "image_url",
                        "image_url": {"url": encoded_image, "detail": "low"},
                    },
                ],
            },
        ]
        return messages
    
    def describe_user_view(self) -> list:
        image_file = self.get_amulet_view()
        encoded_image = self.encode_image(image_file=image_file)
        messages = self.format_vision_inputs(encoded_image=encoded_image) 
        response = self.client.chat.completions.create(
            messages=messages,
            model="gpt-4-vision-preview",
            max_tokens=self.max_vision_tokens,
            temperature=self.vision_temperature,
            tools=self.tools
        )
        #NOW WE NEED TO EITHER GIVE TOOLS TO MODEL IN WHILE TOOL CALLS OR WE NEED TO CALL CHAT MODEL HERE WITH RESPONSE
        return response.choices[0].message.content
        

        


# class ModelWithVisionProxy(Model):
#     # MAKE SURE TO CHANGE `get_user_view` TO `describe_user_view` before using this

#     def vis_response_to_tool_call(self, id: str, content: str):
#         return {
#             "tool_call_id": id,
#             "role": "tool",
#             "name": "get_user_view",
#             "content": content,
#         }

#     def format_vision_inputs(self, encoded_image: str) -> list:
#         vision_prompt = {"role": "system", "content": self.prompts["vision"]}

#         messages = [
#             vision_prompt,
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": None},
#                     {
#                         "type": "image_url",
#                         "image_url": {"url": encoded_image, "detail": "low"},
#                     },
#                 ],
#             },
#         ]
#         return messages
    
    # def get_vision_completion(self, messages: list, image_file) -> dict:
    #     encoded_image = self.encode_image(image_file=image_file)
    #     vision_input = self.format_vision_inputs(encoded_image=encoded_image)
    #     response = self.client.chat.completions.create(
    #         model="gpt-4-vision-preview",
    #         messages=vision_input,
    #         temperature=0.4,
    #         # max_tokens=?
    #     )
    #     vis_response = response.choices[0].message.content
    #     messages[-1].content = vis_response #add to the last tool_call as if the function responded 

    #     response = self.get_chat_completion(
    #         messages=messages, return_tool=True, request_image=False
    #     )

    #     return response
    