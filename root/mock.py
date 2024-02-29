from root.model.tools import ModelTools
from root.model.model import Model
from root.device.amulet import Amulet
from config import Config
from openai import OpenAI
import whisper
from typing import Callable
from gpiozero import Button, LED
import pyaudio
from datetime import datetime
import subprocess
import wave
import numpy as np
from io import BytesIO

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_emissions",
            "description": "Calculate the emissions of an activity or item, and optionally update the user's emissions status with the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity": {
                        "type": "string",
                        "description": "A sequence of words describing the activity/item you want to calculation emissions for. This can not be ambiguous and must be descriptive.",
                    },
                    "activity_value": {
                        "type": "number",
                        "description": "The amount of activity you would like to calculate emissions for. For example, if you would like to calculate emissions for 20 dollars worth of an item, the value would be 20.",
                    },
                    "activity_unit": {
                        "type": "string",
                        "enum": [
                            "money",
                            "count",
                            "kg",
                            "lb",
                            "g",
                            "ton",
                            "t",
                        ],
                        "description": "Specifies the metric that `activity_value` represents. If `activity_value` is a currency amount then pass money, if it represents a count of items pass count, if it is the weight of something pass the correct metric.",
                    },
                    "update_user_emissions": {
                        "type": "boolean",
                        "description": "If True, the function will update the user's emissions status with the result of the calculation. Defaults to False."
                    }
                },
                "required": ["activity", "activity_value", "activity_unit"],
            },
        },
    }, 
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "describe_user_view",
    #         "description": "Get a description of what the user is currently seeing. Useful for example, when a user requests to calculate emissions for 'this' instead of explicitly describing an activity.",
    #         "parameters": {"type": "object", "properties": {}},
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "get_user_emissions",
            "description": "Get the amount of emissions a user has emitted since a given time",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": [
                            "current",
                            "historical",
                            "today",
                            "week",
                            "month",
                            "year",
                        ],
                        "description": "Passing `current` will return the user's current emissions with respect to their budget, `historical` will return the user's total emissions to date, and `today`, `month`, `year` and `week` all return a value for the respective period.",
                    },
                },
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "make_pledge",
    #         "description": "Call this when the user wants to make a pledge to refrain from an emitting activity.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "activity": {
    #                     "type": "string",
    #                     "description": "The activity the user is pledging to refrain from"
    #                 },
    #                 "activity_unit": {
    #                     "type": "string",
    #                     "enum": [
    #                         "money",
    #                         "kg",
    #                         "lb",
    #                         "g",
    #                         "ton",
    #                         "t",
    #                     ],
    #                     "description": "Specifies what the metric of `activity` is. If the user is pledging to avoid spending money on the activity pass money, otherwise pass the correct weight metric. IT CAN ONLY BE `money` OR a valid weight metric"
    #                 },
    #                 "pledge_frequency": {
    #                     "type": "string",
    #                     "enum": ["day", "week", "year"],
    #                     "description": "A string specifying whether the user is pledging to avoid `activity` daily, weekly or yearly. For example, if the user is pledging to buy two less shirts a week you would pass week"
    #                 },
    #                 "activity_value": {
    #                     "type": "number",
    #                     "description": "The amount of `activity` that the user is pledging to refrain from each `pledge_frequency`. For example, if they pledge to buy two less shirts every day, the `activity_value` would be 2."
    #                 },
    #                 "pledge_name": {
    #                     "type": "string",
    #                     "description": "What the user would like to name the pledge. The user MUST choose this name, ask them to if they don't."
    #                 }

    #             },
    #             "required": [
    #                 "activity", "activity_unit", "pledge_frequency", "activity_value", "pledge_name"
    #             ]
    #         }
    #     },
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_user_pledges",
    #         "description": "Get the impact of one or all pledges that the user has made",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "pledge_names": {
    #                     "type": "array",
    #                     "items": {
    #                         "type": "string",
    #                     },
    #                     "description": "An array listing the names of all the pledges you would like to get impacts of. Leave blank to include all pledges."
    #                 },
    #             }
    #         }
    #     }
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_emitting_activities",
    #         "description": "Get the user's emission-causing activites. Useful for informing the user and suggesting pledges.",
    #         "parameters": {"type": "object", "properties": {}}
    #     },
    # },
]

PROMPTS = {
    "chat": "You are a supportive partner helping a user to track and lower their carbon footprint and emissions. Given a query or request from the user, call the most appropriate function to complete your response. When you aren't certain you understand the user's request, ask for more clarification. Respond as concisely and naturally as possible, with basic wording, and in only one to two sentences. Your goal is to help the user live more environmentally friendly.",
    "audio": "The audio is about climate change, and contains words like emissions, carbon footprint, impact, pledges, sustainability, and carbon budget.",
}


class TempModelTools(ModelTools):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompts = PROMPTS
        self.tools = TOOLS
            

    def cosine_similarity(self, x, y):
        norm_x = np.linalg.norm(x)
        norm_y = np.linalg.norm(y)
        return np.dot(x, y) / norm_x * norm_y

    def get_emission_factor(self, activity: str, activity_unit_type: str) -> dict:
        query_embeddings = self.get_embeddings(text=activity)
        similarities = []
        for factor in self.emission_factors.find({"unit_types": activity_unit_type}):
            factor["similarity"] = self.cosine_similarity(
                factor["embeddings"], query_embeddings
            )
            similarities.append(factor)
        return max(similarities, key=lambda x: x["similarity"])
    
    def _calculate(
        self, activity: str, activity_value: int | float, activity_unit: str
    ) -> dict:
        if activity_unit == "count":
            activity_unit_type = "count"
        elif activity_unit == "money":
            activity_unit_type = "money"
            activity_unit = self.savior["currency"]
        elif activity_unit not in ["kWh", "g", "kg", "lb", "t", "ton", "count"]:
            raise ValueError(
                "The unit for activity must be `money` or a valid weight metric"
            )
        else: 
            activity_unit_type = "weight"
            
        emission_factor = self.get_emission_factor(
            activity=activity, activity_unit_type=activity_unit_type
        )
        print("EMISSION FACTOR RESULT", emission_factor)
        return {
            "co2e": emission_factor["co2e"] * activity_value,
            "co2e_unit": "kg",
            "activity_unit_type": activity_unit_type,
            "activity": emission_factor["activity"],
            "activity_unit": activity_unit,
            "activity_value": activity_value,
            "tool_call_query": activity
        }

class TempModel(Model):
    def __init__(self, savior_id: str, amulet_tools: dict[str, Callable]):
        self.client = OpenAI()
        model_tools = TempModelTools(
            embeddings_generator=self.generate_embeddings, savior_id=savior_id
        )
        helpers = model_tools.helpers
        self.tools, tools_to_functions, self.prompts = helpers
        self.tools_to_functions = {**tools_to_functions, **amulet_tools}
        self.tts_voice = model_tools.savior["tts_voice"]
        config = Config()
        self.chat_temperate = config.chat_temperature
        self.vision_temperature = config.vision_temperature
        self.max_vision_tokens = config.max_vision_tokens
        self.audio_input_file = config.audio_input_file
        self.audio_output_file = config.audio_output_file
        self._current_thread = {"last_interaction": datetime.now(), "thread": []}
        # self.whisper_model = whisper.load_model("tiny")
        
    def audio_to_text(self, audio_file: BytesIO):
        print("audio to text called")
        text = self.client.audio.transcriptions.create(
            model="whisper-1", prompt=self.prompts["audio"], file=audio_file,
        )
        audio_file.close()
        return text.text
        
    
    def moderate(self, text: str) -> bool:
        return False
    
from root.device.audio import AudioTools
class TempAmulet(Amulet):

    def __init__(self, savior_id: str):
        print("this is temp amulet with all the bytesio and testing")
        config = Config()
        amulet_tools = {
            "get_view": self.get_view,
            "reject_query": self.reject_query,
        }
        self.model = TempModel(savior_id=savior_id, amulet_tools=amulet_tools)
        audio_button = Button(config.audio_pin, pull_up=False)
        audio_button.when_released = self.handle_query
        wake_led = LED(config.wake_led_pin)
        self.audio_tools = AudioTools(button=audio_button, led=wake_led)
        self.image_input_file = config.image_input_file
        
    def handle_query(self: str) -> None:
        """On release of query sensor, this function calls the model
        with the query and then plays back the response, if any"""
        try:
            audio_bytes = self.audio_tools.audio_bytes
            if audio_bytes:
                audio_output = self.model(audio_file=audio_bytes)
                print(self.model.current_thread)
                if audio_output:
                    self.audio_tools.audio_playback(audio_output)
                    self._cleanup([audio_output])
            else:
                print("The request was flagged silent")
        except Exception as e:
            self.reject_query(e)



# old tool calls
# TOOLS = [
#         {
#                 "type": "function",
#                 "function": {
#                         "name": "get_user_emissions",
#                         "description": "Get the amount of emissions a user has emitted since a given time",
#                         "parameters": {
#                                 "type": "object",
#                                 "properties": {
#                                         "period": {
#                                                 "type": "string",
#                                                 "enum": [
#                                                         "current",
#                                                         "historical",
#                                                         "today",
#                                                         "week",
#                                                         "month",
#                                                         "year",
#                                                 ],
#                                                 "description": "Passing `current` will return the user's current emissions with respect to their budget, `historical` will return the user's total emissions to date, and `today`, `month`, `year` and `week` all return a value for the respective period.",
#                                         },
#                                         # "time_range": {
#                                         # 		"type": "object",
#                                         # 		"description": "A dictionary mapping units of time to values that specify how far back in time to go when totalling emissions. Example: {minutes: 0, days: 1, weeks: 0, years: 0}. Either use this parameter OR `period`, DO NOT use both",
#                                         # },
#                                 },
#                         },
#                 },
#         },
#         {
# 				"type": "function",
# 				"function": {
# 						"name": "calculate_emissions",
# 						"description": "Calculate the emissions of an activity or item.",
# 						"parameters": {
# 								"type": "object",
# 								"properties": {
# 										"activity": {
# 												"type": "string",
# 												"description": "A sequence of words describing the activity/item you want to retrieve an emission factor for.",
# 										},
# 										"activity_value": {
# 												"type": "number",
# 												"description": "The amount of activity you would like to calculate emissions for. For example, if you would like to receive emissions for 20 dollars worth of an item, the value would be 20."
# 										},
# 										"activity_unit": {
# 												"type": "string",
# 												"enum": [
# 														"money",
# 														"kg",
# 														"lb",
# 														"g",
# 														"ton"
# 														"t",
# 												],
# 												"description": "Specifies the metric that the value of `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric."
# 										},
# 										# "activity_unit_type": {
# 										# 		"type": "string",
# 										# 		"enum": ["money", "weight"],
# 										# 		"description": "One of `money` or `weight` which specifies what type of unit `activity_value` represents."
# 										# },
# 										# "activity_unit": {
# 										# 		"type": "string",
# 										# 		"enum": ["g", "kg", "lb", "t", "ton"],
# 										# 		"description": "ONLY use if `activity_value` is a measurement of weight, NOT money, otherwise ignore. If using: pass a metric abbreviation that is non-plural and labels `activity_value`. For example, if an item weighs 10 grams, the activity_unit would be g.",
# 										# },
# 								},
# 								"required": ["activity", "activity_value", "activity_unit"],
# 						},
# 				},

# 		},
#         {
# 				"type": "function",
# 				"function": {
# 						"name": "update_user_emissions",
# 						"description": "Update the user's emissions with a given activity and it's corresponding value.",
# 						"parameters": {
# 								"type": "object",
# 								"properties": {
# 										"activity": {
# 												"type": "string",
# 												"description": "A sequence of words describing the activity/item to calculate emissions for when updating. E.g. buying fruit",
# 										},
# 										"activity_value": {
# 												"type": "number",
# 												"description": "The amount of activity done by the user. For example, if the user bought 10 dollars worth of fruit, you would pass 10",
# 										},
# 										"activity_unit": {
# 												"type": "string",
# 												"enum": [
# 														"money",
# 														"kg",
# 														"lb",
# 														"g",
# 														"ton"
# 														"t",
# 												],
# 												"description": "Specifies what metric the value of `activity_value` represents. If `activity_value` is a currency amount then pass money, if it is the weight of something pass the correct metric."
# 										},
# 										# "activity_unit_type": {
# 										# 		"type": "string",
# 										# 		"enum": ["money", "weight"],
# 										# 		"description": "One of `money` or `weight` which specifies what type of unit `activity_value` represents."
# 										# },
# 										# "activity_unit": {
# 										# 		"type": "string",
# 										# 		"enum": ["g", "kg", "lb", "t", "ton"],
# 										# 		"description": "ONLY use if `activity_value` is a measurement of weight, NOT money, otherwise ignore. If using: pass a metric abbreviation that is non-plural and labels `activity_value`. For example, if an item weighs 10 grams, the activity_unit would be g.",
# 										# },
# 								},
# 								"required": ["activity", "activity_value", "activity_unit"],
# 						},
# 				},
# 		},
# ]
