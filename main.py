from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service

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


COLLECTION_FOLDER_PATH = "Collection"


class ManageObject():
    def __init__(self, url):
        self.driver_path = 'C:\\geckodriver.exe'
        self.manga_url = url

    def start_driver(self):
        cprint("[*] Starting driver...", "green")
        firefox_service = Service(self.driver_path)
        options = webdriver.FirefoxOptions()
        # options.add_argument('--headless')  # run in headless mode (no UI)
        self.driver = webdriver.Firefox(
            service=firefox_service, options=options)

        self.driver.get(url)

        wait = WebDriverWait(self.driver, 10)
        # button = wait.until(EC.element_to_be_clickable((By.ID, 'read-action mrt10')))
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        # Zoom out by 50%
        self.driver.execute_script("document.body.style.zoom='30%'")
        input("Zoom?")

    def loading_data(self):
        if os.path.exists(self.manga_info_path):
            self.data_info = read_json(self.manga_info_path)
            return True
        return False

    def get_manga_info(self):
        cprint("[*] Getting manga information...", "green")
        item_detail = self.driver.find_element(By.ID, "item-detail")
        title = item_detail.find_element(By.CLASS_NAME, "title-detail").text
        author = item_detail.find_element(
            By.CLASS_NAME, format_class("author row")).text.split("\n")[1]
        status = item_detail.find_element(
            By.CLASS_NAME, format_class("status row")).text.split("\n")[1]
        img_src = item_detail.find_element(
            By.TAG_NAME, "img").get_attribute("src")
        print(title, author, status, img_src)

        self.manga_folder_path = os.path.join(COLLECTION_FOLDER_PATH, title)
        self.manga_info_path = os.path.join(
            self.manga_folder_path, "info.json")
        if not os.path.exists("Collection"):
            os.mkdir("Collection")
        if not os.path.exists(self.manga_folder_path):
            os.mkdir(self.manga_folder_path)
        if self.loading_data():
            self.data_info["status"] = status
        else:
            self.data_info = {
                "title": title,
                "author": author,
                "status": status,
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
            filename = f"{self.get_current_chapter()}-page-{str(idx).zfill(4)}.jpg"
            filename = os.path.join(current_chapter_folder_path, filename)
            temp_count = 0
            while True:
                if not os.path.exists(filename):
                    break
                filename = f"{self.get_current_chapter()}-page-{str(idx).zfill(4)}-{str(temp_count).zfill(3)}.jpg"
                filename = os.path.join(current_chapter_folder_path, filename)
                temp_count += 1

            img_base64 = e_img.screenshot_as_base64
            img_data = base64.b64decode(img_base64)
            with open(filename, 'wb') as f:
                f.write(img_data)
        if "downloaded_chapters" in self.data_info.keys():
            self.data_info["downloaded_chapters"].append(
                self.get_current_chapter())
        else:
            self.data_info["downloaded_chapters"] = [
                self.get_current_chapter()]
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
manga = ManageObject(url)
manga.start_driver()
manga.get_manga_info()
manga.start_read_from_beginning()
while True:
    manga.get_all_images()
    is_next = manga.next_chapter()
    if is_next == False:
        break
manga.quit()
