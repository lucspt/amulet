from root.model.tools import TOOLS, PROMPTS

"""Whenever the time is right"""

prompt_setup = PROMPTS["chat"]

self = None
{
"get_user_emissions": self.get_user_emissions,
"calculate_emissions": self.calculate_emissions,
"make_pledge": self.make_pledge,
"get_active_pledges": self.get_active_pledges,
"get_emitting_activities": lambda: str(self.emitting_activities), 
#string instead of object for the model
"get_user_info": lambda: str(self.user_info)}


prompts = [
    #get_user_emissions
    "What are my emissions from the past two weeks?",
    "How much have I emitted this year?",
    "How are my emissions looking?",
    
    #calculate_emissions
    "How much emissions is in a $10, if it is made up of "
    
    
    #updates
    "Update my emissions for a $10 shirt that's 50% cotton and 50% plastic",
]

tool_call_responses = [
    #get_user_emissions
    
    #calculate_emissions
]

examples = [
    
    #get_user_emissions
    {
    
    },
    
    #calculate_emissions
    {
        "messages": [
            {"role": "user", "content": "How much emissions were caused by this $10 shirt? It's made up 80% plastic 20% cotton"},           
        ]
    }
]

REJECTIONS = [
    ""
]
