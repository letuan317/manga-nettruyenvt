from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options

import undetected_chromedriver as uc

from utils import browsers
import time
import os
import requests
import base64
from termcolor import colored, cprint
from alive_progress import alive_bar
import json
import sys


def format_class(class_name):
    return class_name.replace(" ", ".")


def download_image(src, filename):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    response = requests.get(src, headers=headers)
    with open(filename, 'wb') as f:
        f.write(response.content)


def write_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)


def read_json(file_path):
    with open(file_path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)


COLLECTION_FOLDER_PATH = "Collection"


class ChapterClass:
    def __init__(self):
        self.title = ""
        self.author = ""
        self.status = ""
        self.chapters = [],
        self.downloaded = []

    def set(self, data_info):
        try:
            self.title = data_info["title"]
        except:
            pass
        try:
            self.author = ""
        except:
            pass
        try:
            self.status = ""
        except:
            pass
        try:
            self.chapters = []
        except:
            pass
        try:
            self.downloaded = []
        except:
            pass

    def convert_to_json(self):
        return json.dumps(self.__dict__)


class MangaClass:
    def __init__(self, url):
        self.driver_path = 'C:\\geckodriver.exe'
        self.manga_url = url

    def start_driver(self):
        cprint("[*] Starting driver...", "green")
        # firefox_service = Service(self.driver_path)
        # options = webdriver.FirefoxOptions()
        # # options.add_argument('--headless')  # run in headless mode (no UI)
        # self.driver = webdriver.Firefox(
        #     service=firefox_service, options=options)

        uc.install(executable_path='c:/chromedriver.exe', )
        options = uc.ChromeOptions()
        options.headless = False
        self.driver = uc.Chrome(options=options)

        version = self.driver.capabilities['chrome']['chromedriverVersion'].split(' ')[
            0]
        print(colored('Chromedriver version:', "green"),
              colored(version, "yellow"))

        self.driver.get(url)

        wait = WebDriverWait(self.driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        except:
            print("Timed out waiting for page to load")
        input("Zoom?")

    def loading_data(self):
        if os.path.exists(self.manga_info_path):
            self.data_info = read_json(self.manga_info_path)
            return True
        return False

    def get_manga_info(self):
        cprint("[*] Getting manga information...", "green")

        ITEM_CLASS = "item-detail"
        TITLE_CLASS = format_class("title-detail")
        AUTHOR_CLASS = format_class("author row")
        STATUS_CLASS = format_class("status row")

        item_detail = self.driver.find_element(By.ID, ITEM_CLASS)
        title = item_detail.find_element(By.CLASS_NAME, TITLE_CLASS).text
        author = [el.text for el in item_detail.find_elements(
            By.CLASS_NAME, AUTHOR_CLASS) if "Tác giả" in el.text][0].split("\n")[1]
        status = item_detail.find_element(
            By.CLASS_NAME, STATUS_CLASS).text.split("\n")[1]
        img_src = item_detail.find_element(
            By.TAG_NAME, "img").get_attribute("src")

        print(title, author, status, img_src)

        self.manga_folder_path = os.path.join(COLLECTION_FOLDER_PATH, title)
        self.manga_info_path = os.path.join(
            self.manga_folder_path, "info.json")

        create_folder_if_not_exists("Collection")
        create_folder_if_not_exists(self.manga_folder_path)

        if self.loading_data():
            self.data_info["status"] = status
        else:
            self.data_info = {
                "title": title,
                "author": author,
                "status": status,
                "chapters": [],
                "downloaded": []
            }
            download_image(src=img_src, filename=os.path.join(
                self.manga_folder_path, "cover.png"))

        write_json(self.manga_info_path, self.data_info)

    def start_read_from_beginning(self):
        cprint("[*] Starting read from beginning...", "green")
        current_title = self.driver.title
        e_read_action = self.driver.find_element(
            By.CLASS_NAME, format_class("read-action mrt10"))
        es_read_action_buttons = e_read_action.find_elements(By.TAG_NAME, "a")
        for e in es_read_action_buttons:
            if "Đọc từ đầu" in e.text:
                e.click()
                break
        while True:
            if current_title != self.driver.title:
                current_title = self.driver.title
                break
            time.sleep(1)
        if "just a moment" in current_title.lower():
            input("Continue reading")

    def get_all_list_chapters(self):
        nt_listchapter = self.driver.find_element(By.ID, "nt_listchapter")
        es_a = nt_listchapter.find_elements(By.TAG_NAME, "a")
        self.list_chapters = []
        for e_a in es_a:
            self.list_chapters.append(e_a.get_attribute("href"))

    def process_chapters(self):
        chapter = ChapterClass()
        chapter.set(self.data_info)
        chapter.chapters = self.list_chapters
        for i_chapter in self.list_chapters:
            self.driver.get(i_chapter)
            time.sleep(5)
            self.get_all_images()
            chapter.chapters.remove(i_chapter)
            chapter.downloaded.append(i_chapter)
            write_json(self.manga_info_path, chapter.convert_to_json())

    def get_all_images(self):
        cprint("[*] Getting all images...", "green")
        e_reading_detail = self.driver.find_element(
            By.CLASS_NAME, format_class("reading-detail box_doc"))
        es_images = e_reading_detail.find_elements(By.TAG_NAME, "img")
        if len(es_images) == 0:
            return False
        current_chapter_folder_path = os.path.join(
            self.manga_folder_path, self.get_current_chapter())
        if not os.path.exists(current_chapter_folder_path):
            os.mkdir(current_chapter_folder_path)
        for idx, e_img in enumerate(es_images):
            src = "https:" + e_img.get_attribute('src')
            data_index = e_img.get_attribute('data-index')
            filename = f"{self.get_current_chapter()}-page-{str(idx).zfill(4)}.png"
            filename = os.path.join(current_chapter_folder_path, filename)
            temp_count = 0
            while True:
                if not os.path.exists(filename):
                    break
                filename = f"{self.get_current_chapter()}-page-{str(idx).zfill(4)}-{str(temp_count).zfill(3)}.png"
                filename = os.path.join(current_chapter_folder_path, filename)
                temp_count += 1

            # img_base64 = e_img.screenshot_as_base64
            # img_data = base64.b64decode(img_base64)
            # with open(filename, 'wb') as f:
            #     f.write(img_data)
            e_img.screenshot(filename)
        if "downloaded" in self.data_info.keys():
            self.data_info["downloaded"].append(self.driver.current_url)
        else:
            self.data_info["downloaded"] = [self.driver.current_url]
        write_json(self.manga_info_path, self.data_info)

    def next_chapter(self):
        cprint("[*] Nexting chapter...", "green")
        try:
            self.driver.find_element(
                By.CLASS_NAME, format_class("next a_next disabled"))
            return False
        except:
            pass
        try:
            e_next_button = self.driver.find_element(
                By.CLASS_NAME, format_class("next a_next"))
            e_next_button.click()
            time.sleep(5)
            cprint(self.get_current_chapter(), "yellow")
            return True
        except Exception as e:
            cprint(e, "red")
            return False

    def get_current_chapter(self):
        url = self.driver.current_url
        temp_list = url.split("/")
        for i in temp_list:
            if "chap" in i:
                temp = i.split("-")
                return temp[0]+"-"+temp[1].zfill(4)

    def quit(self):
        self.driver.quit()


url = sys.argv[1]
manga = MangaClass("url")
manga.start_driver()
manga.get_manga_info()
manga.start_read_from_beginning()
while True:
    manga.get_all_images()
    is_next = manga.next_chapter()
    if is_next == False:
        break
# manga.get_all_list_chapters()
# manga.process_chapters()
manga.quit()
