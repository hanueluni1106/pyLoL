"""Scrapes observations from a replay file by replaying a match using
the League game client and storing the observations in a json file."""

import os
import time
import json
import subprocess
import base64
import requests


class ReplayScraper(object):
    """League of Legends replay scraper class.
    
    This class handles executing the League of Legends client in
    replay mode and the scraping application in the correct order.
    Args:
        game_dir: League of Legends game directory.
        replay_dir: League of Legends *.rofl replay directory.
        dataset_dir: JSON replay files output directory.
        replay_speed: League of Legends client replay speed multiplier.
        scraper_path: Directory of the scraper program.
    """
    def __init__(self,
            game_dir,
            replay_dir,
            dataset_dir,
            scraper_dir,
            replay_speed=8,
            region="KR"):
        self.game_dir = game_dir
        self.replay_dir = replay_dir
        self.dataset_dir = dataset_dir
        self.scraper_dir = scraper_dir
        self.replay_speed = replay_speed
        self.region = region

    def run_client(self, replay_path, start, end, speed, paused):
        args = [
            str(os.path.join(self.game_dir, "League of Legends.exe")),
            replay_path,
            "-SkipRads",
            "-SkipBuild",
            "-EnableLNP",
            "-UseNewX3D=1",
            "-UseNewX3DFramebuffers=1"]
        print('run lol client:', args)
        subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.game_dir)
        
        '''
        post_running : 리플레이 시작시간, 배속, 일시중지 여부 post 요청 진행 여부, 클라이언트가 리플레이를 돌리기 전까지 계속 요청.
        리플레이 돌리고 post 성공하면 False 로 변환.
        '''
        post_running = True 

        while post_running:
            try:
                time.sleep(1)
                req = requests.post(
                        'https://127.0.0.1:2999/replay/playback',
                        headers={
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        data = json.dumps({
                            "paused": paused,
                            "seeking" : False,   
                            "time": start - 5,
                            "speed": speed
                        }),
                        verify=False
                    )
                #req = requests.get('https://127.0.0.1:2999/replay/playback' , verify = False)
                if req.status_code == 200:
                    print("상태코드 : ",req.status_code , "응답 : ",req)
                    post_running = False
            except:
                time.sleep(1)
                pass

        '''
        replay_running : 리플레이가 실행중인가에 대한 불린 ; 클라이언트가 end 시각까지만 실행하도록
        '''     
        replay_running = True    
        while replay_running:
            try:
                timestamp = requests.get('https://127.0.0.1:2999/replay/playback', verify=False).json()['time']    

                if  end <= timestamp <= end + 2:
                    print(f"리플레이 정상 정지, 요청 종료 시각 : {end}s , 실제 종료 시각{timestamp}s")
                    replay_running  = False

            except:
                time.sleep(1)
                pass

        #클라이언트 종료           
        os.system("taskkill /f /im \"League of Legends.exe\"")       


    def run_scraper(self, output_path, end_time):
        time.sleep()

    def scrape(self, game_id, end_time, delay=2):
        """Scrapes a *.rofl file.
        
        Scrapes an individual replay file using the League of Legends
        game client. Scrapes the replay at faster than real-time speed.
        
        Args:
            game_id: Game ID within `replay_dir` to scrape.
            end_time: Number of seconds to scrape within replay.
            delay: Number of seconds to wait before ending.
        """
        replay_fname = f"{self.region}-{game_id}.rofl"
        replay_path = os.path.join(self.replay_dir, replay_fname)

        output_fname = f"{self.region}-{game_id}.json"
        output_path = os.path.join(self.dataset_dir, output_fname)

        self.run_client(replay_path)
        self.run_scraper(output_path, end_time)

        os.system("taskkill /f /im \"League of Legends.exe\"")
        os.system("taskkill /f /im \"ConsoleApplication.exe\"")
        time.sleep(delay)

    def get_replay_ids(self):
        """Returns all of the *.rofl files within the `replay_dir`."""
        ids = os.listdir(self.replay_dir)
        ids = [fname if fname.endswith(".rofl") else None
                 for fname in ids]
        ids = list(filter(lambda x: x != None, ids))
        ids = [fname.split(".")[0].split("-")[1] for fname in ids]
        return ids
    
    def get_metadata(self, game_id):
        replay_fname = f"{self.region}1-{game_id}.rofl"
        replay_path  = os.path.join(self.replay_dir, replay_fname)
        print(os.path.join(self.replay_dir, replay_fname))

        with open(replay_path, "rb") as f:
            f.seek(262)
            length_field_buffer = f.read(26)
            metadata_offset = length_field_buffer[6:10]
            metadata_length = length_field_buffer[10:14]

            metadata_offset = int.from_bytes(metadata_offset, byteorder='little')
            metadata_length = int.from_bytes(metadata_length, byteorder='little')

            f.seek(metadata_offset)
            replay_metadata = f.read(metadata_length)
            replay_metadata = json.loads(str(replay_metadata, encoding="utf-8"))
            stats_json = json.loads(replay_metadata["statsJson"])

            return replay_metadata, stats_json
        
    def get_replay_dir(self):
        return self.replay_dir
