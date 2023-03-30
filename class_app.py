# -*- coding: utf-8 -*-

import curses
import json
import openai
import os
import re
import threading
import time
from tkinter import Tk, filedialog

class SrtGptTranslator:


    def __init__(self):
        
        # default json file name
        self.config_filename_default = "config.json"    
        # read config file
        self.load_config()


    def __del__(self):
        pass


    def load_config(self):
        # read config.json
        try:
            with open(self.config_filename_default, "r", encoding="utf-8") as f:
                self.config = json.load(f)
                
            if self.check_target_language(self.config['target_language']):
                self.config['target_language'] = self.config['target_language'].lower()
            else:
                self.config['target_language'] = "zh-tw"
                
            if not self.check_api_key(self.config['openai_api_key']):
                self.set_api_key()
                
            self.save_config()
            
        except FileNotFoundError:
            # config.json does not exist Initialize config
            self.json_default()
            self.set_api_key()
            self.save_config()
            self.load_config()
          
          
    def set_api_key(self):
        # set API key
        self.title_show("Set Up openai_API")
        type_API= input("Enter your openai_API:")
        
        if self.check_api_key(type_API):
            self.config['openai_api_key'] = type_API
            self.save_config()
            self.pause("openai_API updated")

        else:
            self.pause("Invalid API! Check:https://platform.openai.com/account/api-keys ")
            if self.check_api_key(self.config['openai_api_key']):
                return 0
            else:
                self.set_api_key()
       
       
    def check_api_key(self, API_KEY):
        # Check if the API key exists or is valid
        openai.api_key = API_KEY
        try:
            openai.Model.list()
            return True
            
        except Exception:
            # openai.error.AuthenticationError
            # Reset openai_api_key
            openai.api_key = None
            return False         


    def set_target_language(self):
        # set target language
        self.title_show("Set Up Target Language")
        type_L = input("Target Language:")
        
        if self.check_target_language(type_L):
            self.config['target_language'] = type_L.lower()
            self.save_config()
        else:    
            print("invalid lang-code! Check the lang-code in config.json")

        self.pause(f"Target language updated to {self.config['target_language']} {self.config['languages'][self.config['target_language']]}")
        
        
    def check_target_language(self, tL): 
        # Check language code
        if tL.lower() in self.config['languages']:
            return True
        else:
            return False
            
            
    def main_process(self, srt_relay = 0):
        # main()
        
        # show title
        self.title_show("New Subtitles")
        
        # get the path of the SRT file to process
        srt_path = self.choose_srt()
        
        if not bool(srt_path):
            self.pause("No file selected. Back to menu")
            return 0

        # read SRT file content
        srt_data = self.open_srt(srt_path)
        
        # custom saving
        ask_path = srt_path    
        
        save_path = os.path.split(ask_path)[0]
        save_srt = f"{os.path.split(ask_path)[1][:-4]}_{self.config['target_language']}_pySrt-GPT.srt"          
        
        if bool(self.config['default_path']):
            self.pause("#Custom save path")
            ask_path = self.ask_newsrt(save_srt)
            
            if (ask_path == srt_path) or not bool(ask_path):
                self.title_show("New Subtitles")
                self.pause("Rejected path. Back to menu")
                return 0

            save_path = os.path.split(ask_path)[0]
            save_srt = os.path.split(ask_path)[1]
        
        # segment the contentt, iterate over the segmented srt_lines list
        srt_lines = self.analysis_srt(srt_data, srt_relay)
        
        if srt_lines == []:
            self.pause("Sequence out of the subtitles")
            return 0
        
        
        # iterate over srt_lines
        for i in srt_lines:
        
            self.title_show(f"Processing #sequence {i[0]}, there're {srt_lines[-1][0]} sequences in total.")
            
            print(f"\nSave path {save_path}")
            print(f"Save filename: {save_srt}")
           
            i_sub = i[2]#.replace("\n"," ")

            # pass i to the handler function executed via threading
            trans_result = self.threading_timeout(i_sub)

            # terminate main_process if error
            if trans_result == None:
                if i[0] != str(srt_relay + 1):
                    print(f"Completed {int(i[0])-1} sequences to {save_srt}")
                    print(f"When the problem solved, continue the #sequence {i[0]}\n")
                else:
                    self.pause("# Error! Back to menu")
                    return 0
                    
                break

            print(f"\n- #sequence {i[0]} Translated ", end = '')
            
            # modifier trans_result string
            trans_result = trans_result.replace('\n','')
            trans_result = re.sub(self.config['ugly_chars'],' ',trans_result)
            trans_result = trans_result.strip()
            
            trans_section = f"{i[0]}\n{i[1]}\n{trans_result}\n\n"     
 
            # append the result line by line to the output
            self.save_newsrt(trans_section, save_path, save_srt)
            print(f"- #sequence {i[0]} Wrote\n")
            
            # continue for loop after config['nap'] seconds
            time.sleep(self.config['nap']) 
            
            
        # display processing message and return while loop
        self.pause("# Back to menu")
        
        
    def threading_timeout(self, part_sub):
        # Call quest_gpt by threading
        thread = threading.Thread(target = self.quest_gpt, args=(part_sub,))
        thread.start()
        thread.join(self.config['time_out']) #request timeout seconds
    
        if thread.is_alive():
            print("\n# Request Time-Out\n")
            return None   
        else:
            return thread.result
    
    
    def quest_gpt(self, part_sub):
        # openai.ChatCompletion.create object call and Error detection
        quest = self.config['PROMPT'].replace("_part_srt_", part_sub).replace("_config_lang_", self.config['target_language'])
        
        print("\nPROMPT:",quest.replace('\n',' '))

        try:
            response = openai.ChatCompletion.create(
                model = self.config['model'],
                temperature = self.config['temperature'],
                messages = [{"role": "user", "content": quest,}],)
            
            print("GPT:",response.choices[0].message.content.strip())
            threading.current_thread().result = response.choices[0].message.content

        except Exception as Er:
            print(f"\nError codes:{type(Er)}\n")
            print(f"{Er}\n")
            threading.current_thread().result = None
            
            
    def choose_srt(self):
        # select source srt file
        return filedialog.askopenfilename(title = "Choose SRT Subtitles File", filetypes=(("Srt File", "*.srt"),))
        
        
    def ask_newsrt(self, ini_f):
        # custom saving
        return filedialog.asksaveasfilename(title = "Save SRT Subtitles File", initialfile =  ini_f, filetypes=(("Srt File", "*.srt"),), defaultextension="*.srt")
        
        
    def save_newsrt(self, section, path, filename):
        # append to new file
        with open(f"{path}\\{filename}", 'a', encoding='utf-8') as f:
            f.write(section)
    
    
    def open_srt(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            print("Source: ",path)
            content = f.read()
        return content
    
    
    def analysis_srt(self, data, relay = 0):
        #regular expression
        pattern_match = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d+ --> \d{2}:\d{2}:\d{2},\d+)\n(.+?(?=\n\d|$))'
        
        matches = re.findall(pattern_match, data, re.DOTALL)
        lines = []
        
        for pop in matches[relay:]:
            lines.append(pop)
        return lines
        
        
    def srt_formatting(self):
        # Bold – <b>…</b> , Italic – <i>…</i> , Underline – <u>…</u>
        pass


    def cls(self):
        os.system('cls')


    def title_show(self, info = ''):
        # Show current title
        self.cls()
        print(f"# pySrt-GPT by jkkgrk - {info}")
        
        print(f"Target Language:{self.config['target_language']} {self.config['languages'][self.config['target_language']]},",
              f"API:{self.config['openai_api_key'][-8:]},",
              f"Time-Out:{self.config['time_out']}s,", 
              f"Custom Path:{'on' if self.config['default_path'] else 'off'}")
       
       
    def pause(self, info = ''):
        # Pause message
        zawarudo = input(f"\n{info} <Enter>")


    def draw_menu(self):
        
        stdscr = curses.initscr()
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
   
        menu = ["# pySrt-GPT by jkkgrk - MENU",

                f"Target Language:{self.config['target_language']} {self.config['languages'][self.config['target_language']]}, " +
                f"API:{self.config['openai_api_key'][-8:]}, " +
                f"Time-Out:{self.config['time_out']}s, " + 
                f"Custom Path:{'on' if self.config['default_path'] else 'off'}",
                
                "(1) New Subtitles", 
                "(2) Continue", 
                "(3) Set Up Target Language", 
                "(4) Set Up openai_API", 
                "(5) Exit "]       
                
        # initial selected
        current_row = 2

        while True:
            # draw menu
            for i, option in enumerate(menu):
                if i == current_row:
                    stdscr.addstr(i, 0, option, curses.A_REVERSE)
                else:
                    stdscr.addstr(i, 0, option)
            # getch to get an integer
            key = stdscr.getch()
            if key == curses.KEY_UP:
                # move up
                current_row = max(2, current_row - 1)
            elif key == curses.KEY_DOWN:
                # move down
                current_row = min(len(menu) - 1, current_row + 1)
            elif key == ord('\n'):
                # selected
                stdscr.refresh()
                curses.napms(10)
                break
            stdscr.refresh()
            
        # end curses
        stdscr.keypad(False)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        
        return current_row-2


    def save_config(self):
        # json.dump updated self.config to self.config_filename_default
        with open(self.config_filename_default, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        
        
    def json_default(self):
        # create default config data
        self.config = {
        "openai_api_key" : 'empty',
        "target_language" : 'zh-tw',
        "PROMPT" : 'TRANSLATE \"_part_srt_\" TO \"_config_lang_\" WITHOUT ANY COMMENT.',
        "model" : 'gpt-3.5-turbo',
        "temperature" : 0.5,
        "time_out" : 5,
        "nap" : 1.25,
        "default_path" : 1,
        "ugly_chars" : r'，|。|"|「|」|｢|｣|【|】',
        "languages" :{
        "ar-sa": "Arabic (Saudi Arabia)",
        "bg-bg": "Bulgarian (Bulgaria)",
        "ca-es": "Catalan (Catalan)",
        "zh-tw": "Chinese (Taiwan)",
        "cs-cz": "Czech (Czech Republic)",
        "da-dk": "Danish (Denmark)",
        "de-de": "German (Germany)",
        "el-gr": "Greek (Greece)",
        "en-us": "English (United States)",
        "fi-fi": "Finnish (Finland)",
        "fr-fr": "French (France)",
        "he-il": "Hebrew (Israel)",
        "hu-hu": "Hungarian (Hungary)",
        "is-is": "Icelandic (Iceland)",
        "it-it": "Italian (Italy)",
        "ja-jp": "Japanese (Japan)",
        "ko-kr": "Korean (Korea)",
        "nl-nl": "Dutch (Netherlands)",
        "nb-no": "Norwegian, Bokm\u00c3\u00a5l (Norway)",
        "pl-pl": "Polish (Poland)",
        "pt-br": "Portuguese (Brazil)",
        "ro-ro": "Romanian (Romania)",
        "ru-ru": "Russian (Russia)",
        "hr-hr": "Croatian (Croatia)",
        "sk-sk": "Slovak (Slovakia)",
        "sq-al": "Albanian (Albania)",
        "sv-se": "Swedish (Sweden)",
        "th-th": "Thai (Thailand)",
        "tr-tr": "Turkish (Turkey)",
        "ur-pk": "Urdu (Islamic Republic of Pakistan)",
        "id-id": "Indonesian (Indonesia)",
        "uk-ua": "Ukrainian (Ukraine)",
        "be-by": "Belarusian (Belarus)",
        "sl-si": "Slovenian (Slovenia)",
        "et-ee": "Estonian (Estonia)",
        "lv-lv": "Latvian (Latvia)",
        "lt-lt": "Lithuanian (Lithuania)",
        "fa-ir": "Persian (Iran)",
        "vi-vn": "Vietnamese (Vietnam)",
        "hy-am": "Armenian (Armenia)",
        "az-latn-az": "Azeri (Latin, Azerbaijan)",
        "eu-es": "Basque (Basque)",
        "mk-mk": "Macedonian (Former Yugoslav Republic of Macedonia)",
        "af-za": "Afrikaans (South Africa)",
        "ka-ge": "Georgian (Georgia)",
        "fo-fo": "Faroese (Faroe Islands)",
        "hi-in": "Hindi (India)",
        "ms-my": "Malay (Malaysia)",
        "kk-kz": "Kazakh (Kazakhstan)",
        "ky-kg": "Kyrgyz (Kyrgyzstan)",
        "sw-ke": "Kiswahili (Kenya)",
        "uz-latn-uz": "Uzbek (Latin, Uzbekistan)",
        "tt-ru": "Tatar (Russia)",
        "pa-in": "Punjabi (India)",
        "gu-in": "Gujarati (India)",
        "ta-in": "Tamil (India)",
        "te-in": "Telugu (India)",
        "kn-in": "Kannada (India)",
        "mr-in": "Marathi (India)",
        "sa-in": "Sanskrit (India)",
        "mn-mn": "Mongolian (Cyrillic, Mongolia)",
        "gl-es": "Galician (Galician)",
        "kok-in": "Konkani (India)",
        "syr-sy": "Syriac (Syria)",
        "dv-mv": "Divehi (Maldives)",
        "ar-iq": "Arabic (Iraq)",
        "zh-cn": "Chinese (People's Republic of China)",
        "de-ch": "German (Switzerland)",
        "en-gb": "English (United Kingdom)",
        "es-mx": "Spanish (Mexico)",
        "fr-be": "French (Belgium)",
        "it-ch": "Italian (Switzerland)",
        "nl-be": "Dutch (Belgium)",
        "nn-no": "Norwegian, Nynorsk (Norway)",
        "pt-pt": "Portuguese (Portugal)",
        "sr-latn-cs": "Serbian (Latin, Serbia)",
        "sv-fi": "Swedish (Finland)",
        "az-cyrl-az": "Azeri (Cyrillic, Azerbaijan)",
        "ms-bn": "Malay (Brunei Darussalam)",
        "uz-cyrl-uz": "Uzbek (Cyrillic, Uzbekistan)",
        "ar-eg": "Arabic (Egypt)",
        "zh-hk": "Chinese (Hong Kong S.A.R.)",
        "de-at": "German (Austria)",
        "en-au": "English (Australia)",
        "es-es": "Spanish (Spain)",
        "fr-ca": "French (Canada)",
        "sr-cyrl-cs": "Serbian (Cyrillic, Serbia)",
        "ar-ly": "Arabic (Libya)",
        "zh-sg": "Chinese (Singapore)",
        "de-lu": "German (Luxembourg)",
        "en-ca": "English (Canada)",
        "es-gt": "Spanish (Guatemala)",
        "fr-ch": "French (Switzerland)",
        "ar-dz": "Arabic (Algeria)",
        "zh-mo": "Chinese (Macao S.A.R.)",
        "de-li": "German (Liechtenstein)",
        "en-nz": "English (New Zealand)",
        "es-cr": "Spanish (Costa Rica)",
        "fr-lu": "French (Luxembourg)",
        "ar-ma": "Arabic (Morocco)",
        "en-ie": "English (Ireland)",
        "es-pa": "Spanish (Panama)",
        "fr-mc": "French (Principality of Monaco)",
        "ar-tn": "Arabic (Tunisia)",
        "en-za": "English (South Africa)",
        "es-do": "Spanish (Dominican Republic)",
        "ar-om": "Arabic (Oman)",
        "en-jm": "English (Jamaica)",
        "es-ve": "Spanish (Venezuela)",
        "ar-ye": "Arabic (Yemen)",
        "en-029": "English (Caribbean)",
        "es-co": "Spanish (Colombia)",
        "ar-sy": "Arabic (Syria)",
        "en-bz": "English (Belize)",
        "es-pe": "Spanish (Peru)",
        "ar-jo": "Arabic (Jordan)",
        "en-tt": "English (Trinidad and Tobago)",
        "es-ar": "Spanish (Argentina)",
        "ar-lb": "Arabic (Lebanon)",
        "en-zw": "English (Zimbabwe)",
        "es-ec": "Spanish (Ecuador)",
        "ar-kw": "Arabic (Kuwait)",
        "en-ph": "English (Republic of the Philippines)",
        "es-cl": "Spanish (Chile)",
        "ar-ae": "Arabic (U.A.E.)",
        "es-uy": "Spanish (Uruguay)",
        "ar-bh": "Arabic (Bahrain)",
        "es-py": "Spanish (Paraguay)",
        "ar-qa": "Arabic (Qatar)",
        "es-bo": "Spanish (Bolivia)",
        "es-sv": "Spanish (El Salvador)",
        "es-hn": "Spanish (Honduras)",
        "es-ni": "Spanish (Nicaragua)",
        "es-pr": "Spanish (Puerto Rico)",
        "sma-no": "Sami, Southern (Norway)",
        "sr-cyrl-ba": "Serbian (Cyrillic, Bosnia and Herzegovina)",
        "zu-za": "Zulu",
        "xh-za": "Xhosa",
        "fy-nl": "Frisian (Netherlands)",
        "tn-za": "Setswana (South Africa)",
        "se-se": "Sami, Northern (Sweden)",
        "sma-se": "Sami, Southern (Sweden)",
        "fil-ph": "Filipino (Philippines)",
        "smn-fi": "Sami, Inari (Finland)",
        "quz-pe": "Quechua (Peru)",
        "se-fi": "Sami, Northern (Finland)",
        "sms-fi": "Sami, Skolt (Finland)",
        "cy-gb": "Welsh",
        "hr-ba": "Croatian (Bosnia and Herzegovina)",
        "iu-latn-ca": "Inuktitut (Latin, Canada)",
        "bs-cyrl-ba": "Bosnian (Cyrillic, Bosnia and Herzegovina)",
        "moh-ca": "Mohawk (Mohawk)",
        "smj-no": "Sami, Lule (Norway)",
        "arn-cl": "Mapudungun (Chile)",
        "mi-nz": "Maori",
        "quz-ec": "Quechua (Ecuador)",
        "ga-ie": "Irish (Ireland)",
        "rm-ch": "Romansh (Switzerland)",
        "sr-latn-ba": "Serbian (Latin, Bosnia and Herzegovina)",
        "smj-se": "Sami, Lule (Sweden)",
        "lb-lu": "Luxembourgish (Luxembourg)",
        "ns-za": "Sesotho sa Leboa (South Africa)",
        "quz-bo": "Quechua (Bolivia)",
        "se-no": "Sami, Northern (Norway)",
        "mt-mt": "Maltese",
        "bs-latn-ba": "Bosnian (Latin, Bosnia and Herzegovina)"}
        }
