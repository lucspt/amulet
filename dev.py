"""

***MODEL CHECKLIST***
    function: get_user_emissions:
        cases: 
        [x] understands the `period` argument for all enum cases
        [] can utilize the time_delta argument.
            today we can try:
                what are my emissions for the past 2 hours?
                it doesn't even try to use it maybe it needs better description in tools
        
    function: calculate_emission & update_user_emissions:
        [x] understands arguments - for what we have tried, yes it seems so
                
***THINGS TO OPTIMIZE***
    [] tts output speed
    [] emission factors, unit types, differentation between them, etc.
    [] the model's output length, potential stopwords or max output length, but preferably just better prompt engineering.
    [] temperature param
        
        
***POSSIBLE ENHANCEMENTS***
    [] giving model an option to get historical threads through mongodb
    [] giving a sample response in each function return 
    
***POSSIBILITES***
    [] what happens when a silent audio file is sent to whisper / model, and how can we prevent it?

***LOGS***
    How much co2 is $10 of plastic worth? [PASSED] - calculate emissions
    Update my emissions for $10 worth of plastic [PASSED] - update emissions (merged with calculate)
    What are my emissions from the past 2 weeks? [NOT PASSED] - get user emissions (time_delta arg)
    update my emissions for one bananna: [TEST MORE THOROUGHLY]
    what does the model say when we ask, what's a sustainable activity for me and my friends tonight? [Passed listed out stuff]
    what's a sustainable alternative to plastic bottled water [Passed said reusable water bottle]
    is $10 worth of beans within my carbon budget? [our function threw an error but it called it correctly]
    Update my emissions for this $10 plastic water bottle and also tell me what's left of my budget after the update [passed]
    update my emissions for 1 shirt 2 pairs of boxers and one pair of pants [ we had to guide the model quite a bit, but it eventually did calculated correctly]
    



***AGENDA***
 [] figure out pledges flow
 [] iterate testing more until we are satisfied (this will take the most time but is main priority concerning the model now)
 [] come up with new tools along the way and new ideas
 [] try out web search api
 [] prompt engineering
 
 ***Specifics***
  the model does not seem to know how to use the timedelta parameter as of now, we should try to figure that out as a next step.
    we could try giving model the period argument as str "2 weeks" instead of {weeks: 2} timedelta and then we implement the correct logic from there. 
    so we have that ready to try for tomorrow, we'll start trying with the kwargs and if not then the string
  
  [] time_delta argument in get user emissions
        let's set up just one function that uses timedelta and try to see if some prompt engineering can help it
  
  
  [] get_pledge_impacts pledge_names -- can it be list or just strings?
        what are the impacts of my pledges so far?
  
  [] make pledge it's getting there, but before continuing we should work on out implementation 
        test how the model uses pledge frequency
        we should try adding: "if the user's request is ambiguous, ask them for more information." to the prompt 
        "Make a pledge to buy two less shirts every day. Name it buying less clothes" 
    
        pledge_frequency: "daily, weekly, etc"    
        
**Agenda for Today:
    1. quick one first 
        [Passed, just needed to do str.lower()] 
        get_pledge_impacts pledge_names -- can it be list or just strings?
        what are the impacts of my pledges?

    2. [Done, can improve but model understands] 
        weve got to try out new make_pledge with activity value now
        something like: make a pledge to buy $10 less plastic every day
        what would you like the pledge_name to be?
        ten plastic
        
    3. [Not tested, not sure if this is still desirable, at least for now]
        test out mongodb queries
     
more generic and general questions:
    what are sustainable groceries to buy?
    what are sustainable restaurants near me? would have to be with web search somehow  
    tell me yummy sustainable recipes     
    what's causing most of my emissions?
        
**Checklist
    1. the model is passing it's own pledge_name, is this undesirable or fine?
    
    2. Do you have any sustainable tips for today?
    
    3. What are my all time emissions? / total emissions
    
    4. the model scrambles when trying to calculate two emissions at once
    
    more general stuff:
        find the most costly part of the model call in terms of speed - see a1
        also decide whether we should be giving emissions budget and extra info in function responses, or if we should give the model access to the user_info attr. or both
        
        a1: So basically it seems like the first call on startup is significantly slower than other calls, and that whisper takes the longest out of all
        and of course the length of the request will affect that. We tried implementing a stream to whisper, 
        but it seems to break up the audio not so greatly, and we need great transcriptions lol. It feels like the calls that are not on startup
        are much faster though, by a lot, we have to test it out more and analyze before optimizing.
        
        let's try to figure out some plans for speed 
        and also how to better deal with current thread
        
        also what about blank audio sent to whisper how can we prevent even calling the model
            we can detect volume either while or after recording - so we have implemented this but have yet to test it 
        
        the model can reply, but the replies can be better and shorter 
        WHENEVER YOU CAN, KEEP YOUR RESPONSES AS SHORT AS ONE SENTENCE.
        
        what are the most impactful sustainable swaps I can make?
        
        a remember functino when the user says remember this for me.
        
        so basically how can we better keep track of the current thread?
        don't think it's exactly a problem about resetting it after 10 minutes
        but over the long run, the model should be able to learn about the savior,
        so that they don't have to repeat themselves of things.
        the remember function would work for that honestly lol.
        
    **Struggles
        the model can't calculates a query of: $10 dollar shirt, half cotton, half plastic... 
            It just passes calculate_emissions("shirt", 10, "money")

        right now it's getting harsh, but it's not as bad as it seems really 
        to really solve it we have to figure out the emission factors
        from there it should be more straight forward stuff, but the emission factors require more.
        
        it almost feels like we shouldn't let the other `struggles` be focused on 
        until we figure out the emission factors
        so what are the solutions for them?

"""

import numpy as np
from root.mock import TempModelTools

mt = TempModelTools(
    savior_id = "123", embeddings_generator=lambda text: np.random.randn(1536)
)
# print(mt.calculate_emissions("", 3, "money", update_user_emissions=False))
# ttf = mt.helpers[1]
# print(ttf["get_user_emissions"](period="current", from_tool_call=False))