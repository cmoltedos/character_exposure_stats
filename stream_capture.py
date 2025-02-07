import os
import requests, pickle
import datetime
import re
import time
from Crypto.Cipher import AES
from optparse import OptionParser
from pdb import set_trace

USER_AGENT = 'Mozilla/5.0'

def input_args():
    parser = OptionParser()
    parser.add_option("-c", "--channel",
                      dest="channel", default='tvn',
                      help="Channel id [default: tvn].\n"
                           "Options: tvn, mega")
    (options, args) = parser.parse_args()
    return options


def canal_13_token_decrypt(token_encripted):
    letters_1 = list(token_encripted)
    letters_2 = list(token_encripted)
    letters_amount = len(letters_1)
    factor_1 = int(int(time.time() * 1000) / 3600000)
    factor_2 = int(int(time.time() * 1000) / 3600000) - 1
    for i in range(letters_amount, 0, -1):
        pos = i - 1
        var_1 = pos * factor_1 % letters_amount
        var_2 = pos * factor_2 % letters_amount
        letters_1[pos], letters_1[var_1] = letters_1[var_1], letters_1[pos]
        letters_2[pos], letters_2[var_2] = letters_2[var_2], letters_2[pos]
    string2 = ''.join(letters_1)
    sub_string = string2[letters_amount - 2:letters_amount]
    if sub_string == 'OK':
        return string2[:-2]
    string2 = ''.join(letters_2)
    return string2[:-2]


def decrypt_ts_files(content, key_uri):
    key = requests.get(url=key_uri)
    key_content = key.content
    decipher = AES.new(key_content, AES.MODE_CBC, b'0'*16)
    content_decipher = decipher.decrypt(content)
    return content_decipher


class LiveStream(object):

    def __init__(self, channel=None):
        self.channel = channel
        self.rsession = self.create_request_session()
        self.token_function, self.link = self.channel_config()
        try:
            self.token = self.token_function()
            if self.channel == '13':
                self.links_by_resolution = self.get_13_init_urls_stream()
            else:
                self.config_data = self.get_stream_config_data()
                self.links_by_resolution = self.get_init_urls_stream()
        except AttributeError:
            self.links_by_resolution = {}

    def channel_config(self):
        channel_config = {
            'tvn': (self.get_token_tvn, '57a498c4d7b86d600e5461cb'),
            'mega': (self.get_token_mega, 'https://www.mega.cl/senal-en-vivo/'),
            '13': (self.get_token_13, 'https://www.13.cl/en-vivo'),
            'chv': (self.get_token_chv, 'https://www.chilevision.cl/senal-online')
        }
        if self.channel not in channel_config:
            raise IOError('Channel not supported')
        return channel_config[self.channel]

    def get_token_chv(self, ommit_cache=False):
        html = self.rsession.get(url=self.link).text
        player_js_url = re.search("id=\"mdstrm-player\".*?src='(.*?)'", html, re.DOTALL).group(1)
        player_js = self.rsession.get(url=player_js_url).text
        token = re.search("token = '(.*?)';", player_js, re.DOTALL).group(1)
        self.channel_id = re.search("id = '(.*?)';", player_js, re.DOTALL).group(1)

        token_cache_filename = f'token_cache_{self.channel}_{self.channel_id}.txt'
        if not ommit_cache and os.path.exists(token_cache_filename):
            with open(token_cache_filename) as token_file:
                token = token_file.read()
                print(f"CACHE HIT: CHV token ({token})")
                return token
        with open(token_cache_filename, 'w') as token_file:
            token_file.write(token)
        print(f"CACHE MISS: New CHV token ({token})")
        return token

    def get_token_13(self, ommit_cache=False):
        html = self.rsession.get(url=self.link).text
        encripted_token = re.search("function playerLive.*?"
                                    "'([a-zA-Z0-9]*)'\) \|\| ", html,
                                    re.DOTALL).group(1)
        self.channel_id = canal_13_token_decrypt(encripted_token)

        token_cache_filename = f'token_cache_{self.channel}_{self.channel_id}.txt'
        if not ommit_cache and os.path.exists(token_cache_filename):
            with open(token_cache_filename) as token_file:
                token = token_file.read()
                print(f"CACHE HIT: 13 token ({token})")
                return token
        token_url = 'https://past-server.nedp.io/token/cl-canal13-canal13'
        params = {'rsk': self.channel_id}
        result = self.rsession.get(url=token_url, params=params)
        token = result.json()['token']
        with open(token_cache_filename, 'w') as token_file:
            token_file.write(token)
        print(f"CACHE MISS: New 13 token ({token})")
        return token

    def get_token_mega(self, ommit_cache=False):
        html = self.rsession.get(url=self.link).text
        self.channel_id, server_key = re.search("video = {id: '(.*?)'.*?"
                                                "serverKey : '(.*?)'", html,
                                                re.DOTALL).groups()
        token_cache_filename = f'token_cache_{self.channel}_{self.channel_id}.txt'

        if not ommit_cache and os.path.exists(token_cache_filename):
            with open(token_cache_filename) as token_file:
                token = token_file.read()
                print(f"CACHE HIT: Mega token ({token})")
                return token
        params = {
            'id': self.channel_id, 'type': 'live' if self.is_live else 'media',
            'process': 'access_token', 'key': server_key, 'ua': USER_AGENT
        }

        headers = {'Origin': 'https://www.mega.cl', 'User-Agent': USER_AGENT}
        url = 'https://api.mega.cl/api/v1/mdstrm'
        result = self.rsession.get(url=url, params=params, headers=headers)
        token = result.json()['access_token']
        with open(token_cache_filename, 'w') as token_file:
            token_file.write(token)
        print(f"CACHE MISS: New Mega token ({token})")
        return token

    def get_token_tvn(self, ommit_cache=False):
        self.channel_id = self.link
        token_cache_filename = f'token_cache_{self.channel}_{self.channel_id}.txt'
        if not ommit_cache and os.path.exists(token_cache_filename):
            with open(token_cache_filename) as token_file:
                token = token_file.read()
                print(f"CACHE HIT: TVN token ({token})")
                return token
        token_url = 'https://token.tvn.cl/'
        params = {'url': self.link}
        result = self.rsession.get(url=token_url, params=params).text
        var = re.search('.*MediastreamPlayer\d?\(DivId, (.*?)\);',
                        result).group(1)
        token = re.search(f"^.*?{var} = .*?access_token: '(.*?)',", result,
                          re.DOTALL).group(1)

        with open(token_cache_filename, 'w') as token_file:
            token_file.write(token)
        print(f"CACHE MISS: New TVN token ({token})")
        return token

    def get_stream_config_data(self):
        config_data = dict()
        params = {
            'jsapi': "true", 'autoplay': "true",
            'access_token': self.token, 'mse': "true"
        }
        url = f'https://mdstrm.com/live-stream/{self.channel_id}'
        retries = 3
        while retries:
            result = self.rsession.get(url=url, params=params)
            result_html = result.text
            try:
                config_data['account_id'] = re.search(
                    ".*\"accountID\":\"([A-Za-z0-9]*)\"", result_html, re.DOTALL
                ).group(1)
                break
            except:
                print("[WARNING] Actual token didn't work, getting new one.")
                self.token = self.token_function(ommit_cache=True)
                params['access_token'] = self.token
                retries -= 1
                if retries == 0:
                    set_trace()
                    raise ConnectionError("Token fail to get data")

        config_data['playback_id'] = re.search(".*MDSTRMPID = '([A-Za-z0-9]*)'", result_html, re.DOTALL).group(1)
        config_data['session_id'] = re.search(".*MDSTRMSID = '([A-Za-z0-9]*)'", result_html, re.DOTALL).group(1)
        config_data['unique_id'] = re.search(".*MDSTRMUID = '([A-Za-z0-9]*)'", result_html, re.DOTALL).group(1)
        config_data['version'] = re.search(".*VERSION = '(.*?)'", result_html, re.DOTALL).group(1)
        return config_data

    def get_init_urls_stream(self):
        params = {
            'uid': self.config_data['unique_id'],
            'sid': self.config_data['session_id'],
            'pid': self.config_data['playback_id'],
            'av': self.config_data['version'],
            'access_token': self.token,
            'an': 'screen', 'at': 'web-app', 'ref': '',
            'res': '1280x720', 'dnt': 'true'
        }
        url = f'https://mdstrm.com/live-stream-playlist/{self.channel_id}.m3u8'
        response = self.rsession.get(url=url, params=params)
        result = response.text
        links_by_resolution = dict(re.findall("RESOLUTION=[0-9]{3,4}x([0-9]{3,4}).*?\n([a-zA-Z0-9:/\-\.&?=_%]+)", result, re.DOTALL))

        for resolution, link in links_by_resolution.items():
            if link.startswith('http'):
                break
            link_server = re.search("&es=(.*?)&", link, re.DOTALL).group(1)
            links_by_resolution[resolution] = f'https://{link_server}{link}'

        resolutions = sorted(links_by_resolution.keys(), key=lambda x: int(x))
        print(f"[INFO] Available resolutions: {resolutions}")
        return links_by_resolution

    def get_available_resolution(self):
        return sorted(self.links_by_resolution.keys(),
                      key=lambda x: int(x), reverse=True)

    def get_13_init_urls_stream(self):
        base_url = 'https://cl-canal13-canal13-live.ned.media'
        url = f'{base_url}/live.m3u8'
        params = {'iut': self.token}
        result = self.rsession.post(url=url, params=params)
        manifest_url = result.json()['manifestUrl']
        url2 = f'{base_url}{manifest_url}'
        url3 = f'{base_url}/v1/'

        result = self.rsession.get(url=url2).text
        links_by_resolution = dict(re.findall("RESOLUTION=[0-9]{3,4}x([0-9]{3,4}).*?\n(.*?)\n", result, re.DOTALL))

        for resolution in links_by_resolution:
            links_by_resolution[resolution] = url3 + links_by_resolution[resolution].lstrip('./')
        print(f"[INFO] Available resolutions: {links_by_resolution.keys()}")
        return links_by_resolution

    def get_streaming_file_list(self, resolution):
        link_by_resolution = self.links_by_resolution[resolution]
        if self.channel == 'mega':
            origin = 'https://www.mega.cl'
            headers = {'Origin': origin, 'User-Agent': USER_AGENT}
        else:
            headers = {}
        result = self.rsession.get(url=link_by_resolution, headers=headers)
        if result.status_code != 200:
            raise ConnectionError(f"Error retrieving ({result.status_code}) data for {link_by_resolution}")
        result_content = result.text
        duration_sec = int(re.search("^.*?TARGETDURATION:(\d*)", result_content, re.DOTALL).group(1))
        encrypt_data = re.search("^.*?EXT-X-KEY:(.*?)\n", result_content, re.DOTALL)
        if encrypt_data:
            key_uri = re.search(".*?URI=\"(.*?)\"", encrypt_data.group(1)).group(1)
        else:
            key_uri = None
        links = re.findall("\n(.*?\.ts.*?)\n", result_content)
        if not links[0].startswith('http'):
            prev_code = '/'.join(link_by_resolution.split('/')[:-1])
            links = [f'{prev_code}/{link}' for link in links]
            key_uri = f'{prev_code}/{key_uri}'
        return links, duration_sec, key_uri

    def get_n_second_batches(self, seconds=10, resolution='720', folder = ''):
        total_time = batch_time = 0
        result_filename = f'result_{self.channel}_{self.channel_id}.ts'
        result_route = os.path.join(folder, result_filename)
        consume_ts_urls = set()
        last_time = time.time()
        while total_time < seconds:
            with open(result_route, 'wb') as _:
                pass
            actual_time = time.time()
            seconds_between_last_batch = int(actual_time - last_time)
            last_time = actual_time
            sleep_time = int(batch_time * 0.8) - seconds_between_last_batch
            if sleep_time > 0:
                time.sleep(sleep_time)
            ts_urls, sec_each, key_uri = self.get_streaming_file_list(resolution)
            total_ts = len(set(ts_urls) - consume_ts_urls)
            if batch_time == 0:
                batch_time = total_ts * sec_each
            print(f"[INFO] Downloading {total_ts} video sections")
            for i, ts_url in enumerate(ts_urls):
                if ts_url in consume_ts_urls:
                    continue
                consume_ts_urls.add(ts_url)
                total_time += sec_each
                content = self.rsession.get(url=ts_url).content
                if key_uri:
                    content = decrypt_ts_files(content, key_uri)
                with open(result_route, 'ab') as result_file:
                    result_file.write(content)
            yield result_route


    def create_request_session(self):
        rsession = requests.session()
        cookies_filename = f'cookies_{self.channel}'
        if os.path.exists(cookies_filename):
            with open(cookies_filename, 'rb') as f:
                rsession.cookies.update(pickle.load(f))
        return rsession

    def __exit__(self, exc_type, exc_val, exc_tb):
        cookies_filename = f'cookies_{self.channel}'
        with open(cookies_filename, 'wb') as f:
            pickle.dump(self.rsession.cookies, f)
        return None


def do_work(opt):
    stream = LiveStream(channel=opt.channel.lower())
    resolution = str(input(f'Insert a resolution: '))
    stream.get_n_second_batches(resolution=resolution)


if __name__ == '__main__':
    init = datetime.datetime.now()
    opt = input_args()
    do_work(opt)
    print(f"[INFO] Process finish in in {datetime.datetime.now() - init}")