# from root.mock import TempModelTools
# import numpy as np

# mt = TempModelTools(user_id="123", embeddings_generator=lambda text: np.random.randn(1536))
# print(mt.get_user_emissions("historical"))

"""
**Checklist
    1. the model is passing it's own pledge_name, is this undesirable or fine?
    
    2. what does the model say when we ask, what's a sustainable activity for me and my friends tonight?
    2 continued: how does the model handle a request for sustainable alternatives to an activity:
        what's a sustainable alternative to plastic bottled water
    
    3. if I buy 10 dollars worth of beans, what would my carbon budget be at?
        Is 10 dollars worth of beans within my carbon budget? 
    
    4. Update my emissions for this $10 plastic water bottle and also tell me what's left of my budget after the update
    
    [this one is iffy, but it knows to call the function twice which is good, and it also asks for more info like money / weight]
    5. Multiple activites at once:
        update my emissions for 1 shirt 2 pairs of boxers and one pair of pants
        it should call three different calculations
    
    6. Do you have any sustainable tips today?
    
    more general stuff:
        find the most costly part of the model call in terms of speed
        also decide whether we should be giving emissions budget and extra info in function responses, or if we should give the model access to the user_info attr. or both
"""

from signal import pause
from root.mock import TempAmulet, TempModelTools
# # UNCOMMENT TOOL CALL!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
am = TempAmulet(savior_id="123")
print(am.model.tools)
pause()

# import numpy as np 
# mt = TempModelTools(savior_id="123", embeddings_generator=np.random.rand(1536))
# print(mt.get_active_pledges())

# from root.device.audio import AudioTools
# from gpiozero import Button, LED
# from signal import pause

# import wave
# def check():
#     audio_bytes = audio_tools.audio_bytes
#     if audio_bytes:
#         with wave.open("testing123.wav", "wb") as wf:
#                 wf.setnchannels(audio_tools.channels)
#                 wf.setsampwidth(audio_tools.p.get_sample_size(audio_tools.format))
#                 wf.setframerate(audio_tools.sample_rate)
#                 wf.writeframes(audio_bytes.getvalue())
#                 print("Done!", "read:", audio_bytes.read()[:10], "name: ", audio_bytes.name)
#     else: print("silence")
    
# audio_button = Button(17, pull_up=False)
# wake_led = LED(4)
# audio_tools = AudioTools(button=audio_button, led=wake_led)
# audio_button.when_released = check
# pause()
