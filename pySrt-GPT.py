# -*- coding: utf-8 -*-

import class_app

# create SRTTranslator object
# initialize __init__ in SrtTranslator
sgt = class_app.SrtGptTranslator()

# inf while run
while True:

    sgt.cls()

    # Show menu

    choice = sgt.draw_menu()

    #choice = int(input("0~4:"))
    # operate according to the choice
    match (choice):
    
        case (0):
        # main_process
            sgt.main_process()
        
        case (1):
        # main_process with initial value
            sgt.title_show("Continue the #sequence")
            try:
                relay = int(input("\nContinue the #sequence n = "))
                
                if relay < 1:
                    relay = 0
                else:
                    relay = relay - 1
            
            except ValueError:
                sgt.pause("Input Error")
                continue

            sgt.main_process(relay)
        
        case (2):
            # target_language setting
            sgt.set_target_language()
        
        case (3):
            # OpenAI API setting
            sgt.set_api_key()
        
        case (4):   
            # exit
            break
            
