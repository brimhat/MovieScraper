from selenium import webdriver
from datetime import datetime, timedelta
import time

from selenium.common import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

class MovieDescription:
    def __init__(self, title, date, time, notes, link, location, source):
        self.title = title
        self.date = date
        self.time = time
        self.notes = notes
        self.link = link
        self.location = location
        self.source = source

    def __lt__(self, other):
        return self.get_standardized_date() < other.get_standardized_date()

    def get_title(self):
        return self.title

    def get_date(self):
        return self.date

    def get_time(self):
        return self.time

    def to_list(self):
        return [self.title, self.date, self.time, self.location, self.notes, self.link]

    def get_time_as_float(self):
        timeStr = self.time.split()
        [hoursStr, minutesStr] = timeStr[0].split(':')
        hours = float(hoursStr)
        minutes = float(minutesStr)
        meridiem = 0
        if timeStr[1].upper() == 'PM': meridiem = 12.0
        return hours + (minutes / 60.0) + meridiem

    def get_standardized_date(self):
        if self.source == "AC":
            return datetime.strptime(self.date + "; " + self.time[0:-2] + " " + self.time[-2:], "%a %b %d, %Y; %I:%M %p")
        elif self.source == "VD":
            return datetime.strptime(self.date + "; " + self.time[0:-2] + " " + self.time[-2:], "%b %d, %Y; %I:%M %p")
        elif self.source == "AM":
            return datetime.strptime(self.date + "; " + self.time[0:-2] + " " + self.time[-2:], "%b %d, %Y; %I:%M %p")
        elif self.source == "VT":
            return datetime.strptime(self.date + "; " + self.time[0:-2] + " " + self.time[-2:], "%b %d, %Y; %I:%M %p")
        else:
            raise ValueError("Unrecognized movie source: " + self.source)

    def set_title(self, title):
        self.title = title

    def set_date(self, date):
        self.date = date

    def set_time(self, time):
        self.time = time

    def set_title_and_notes_from_ac(self, str):
        full_title = str.split()
        start_idx = 0
        end_idx = len(str)
        for word in full_title:
            word_index = full_title.index(word)
            if word == "Present" or word == "Presents":
                for i in range(0, word_index + 1):
                    start_idx += len(full_title[i]) + 1  # accounts for whitespace
            elif word == "in":
                for w in full_title[word_index:]:
                    end_idx -= len(w) + 1
        self.title = str[start_idx:end_idx]

        if start_idx > 0: self.notes.append(str[0:start_idx-1])
        if end_idx < len(str): self.notes.append(str[end_idx+1:].capitalize())

def fetch_from_ac_by_date(start_date, end_date):
    movies = []
    url = f"https://www.americancinematheque.com/now-showing/?start={start_date.strftime("%Y.%m.%d")}&end={end_date.strftime("%Y.%m.%d")}&view_type=list"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(1)
    pages = driver.find_elements(By.CLASS_NAME, "ais-Pagination-item")
    for page in pages:
        ActionChains(driver).click(page).perform()
        time.sleep(1)

        elements = driver.find_elements(By.CLASS_NAME, "seriesEventCardModule ")

        for element in elements:
            movie_date = element.find_element(By.CLASS_NAME, "seriesEventCardModule__date").text
            movie_time = element.find_element(By.CLASS_NAME, "seriesEventCardModule__time").text
            movie_title = element.find_element(By.CLASS_NAME, "seriesEventCardModule__title").text
            movie_link = element.find_element(By.CLASS_NAME, "seriesEventCardModule__target").get_attribute("href")
            movie_loc = element.find_element(By.CLASS_NAME, "seriesEventCardModule__body").text.split(" | ")[0]

            movie = MovieDescription(movie_title, movie_date, movie_time, notes=[], link=movie_link, location=movie_loc, source="AC")

            if movie.get_standardized_date() > end_date:
                driver.quit()
                return movies

            movie.set_title_and_notes_from_ac(movie.title)
            movies.append(movie)

        if pages.index(page) == len(pages) - 3: break
    driver.quit()
    return movies

def fetch_from_vd_by_date(start_date, end_date):
    movies = []
    url = f"https://vidiotsfoundation.org/coming-soon/"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(1)
    movie_listings = driver.find_elements(By.CLASS_NAME, "show-details")
    for listing in movie_listings:
        movie_title = listing.find_element(By.CLASS_NAME, "title").text
        movie_link = listing.find_element(By.CLASS_NAME, "title").get_attribute("href")
        movie_dates = listing.find_element(By.ID, "show-datelist-dates").find_elements(By.TAG_NAME, "li")
        movie_times = listing.find_element(By.CLASS_NAME, "showtimes").find_elements(By.TAG_NAME, "li")

        [first_date_month, first_date_day] = movie_dates[0].get_attribute("textContent").split()[1:]
        first_date = f"{datetime.today().year}.{first_date_month}.{first_date_day}"
        if datetime.strptime(first_date, "%Y.%b.%d") > end_date:
            break

        format_note_child = listing.find_element(By.CLASS_NAME, "show-specs").find_element(By.XPATH, ".//*[contains(text(), 'Format:')]")
        format_note = "In " + format_note_child.find_element(By.XPATH, "..").text[8:].split()[0]

        movie_time_index = 0
        for movie_date_dirty in movie_dates:
            movie_date = movie_date_dirty.get_attribute("textContent").strip()[4:].strip() + f", {datetime.today().year}"
            try:
                standardized_date = datetime.strptime(movie_date, "%b %d, %Y")
            except ValueError:
                movie_date = movie_date_dirty.get_attribute("textContent").strip()[8:].strip() + f", {datetime.today().year}"
                standardized_date = datetime.strptime(movie_date, "%b %d, %Y")

            if standardized_date < start_date:
                continue
            if standardized_date > end_date:
                break

            for movie_time_dirty in movie_times[movie_time_index:]:
                if movie_date_dirty.get_attribute("data-date") == movie_time_dirty.get_attribute("data-date"):
                    movie_time_clean = movie_time_dirty.get_attribute("textContent").strip().split("\n")
                    movie_time = movie_time_clean[0]
                    movie_notes = [ format_note ]
                    if len(movie_time_clean) > 1 and len(movie_time_clean[-1].strip()) > 0:
                        movie_notes.append(movie_time_clean[-1].strip())
                    movie = MovieDescription(
                        movie_title,
                        movie_date,
                        movie_time,
                        movie_notes,
                        movie_link,
                        location="Vidiots",
                        source="VD"
                    )
                    movies.append(movie)
                    movie_time_index += 1
    driver.quit()
    return movies

def fetch_from_am_by_date(start_date, end_date):
    movies = []
    url = f"https://www.academymuseum.org/calendar?programTypes=16i3uOYQwism7sMDhIQr2O&start={start_date.strftime("%Y-%m-%d")}&end={end_date.strftime("%Y-%m-%d")}"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(1)
    #driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection").click()
    pages = driver.find_elements(By.CLASS_NAME, "Pagination__PageButton-sc-f6c329e-8")
    for page in pages:
        driver.execute_script("arguments[0].click();", page)
        print("click completed")
        time.sleep(2)

        movie_listings = driver.find_elements(By.CLASS_NAME, "styles__EventCardWrapper-sc-d3de435b-0")
        for listing in movie_listings:
            movie_detail_arr = listing.find_element(By.CLASS_NAME, "styles__Showtime-sc-d3de435b-13").text.split(" | ")
            movie_date = movie_detail_arr[0]
            if datetime.strptime(movie_date, "%b %d, %Y") > end_date:
                driver.quit()
                return movies

            movie_time_dirty = movie_detail_arr[1]
            if len(movie_time_dirty.split(":")) == 1:
                movie_time = movie_time_dirty[0:-2] + ":00 " + movie_time_dirty[-2:]
            else:
                movie_time = movie_time_dirty

            movie_notes = ["In DCP"]
            if len(movie_detail_arr) > 2:
                movie_notes = ["In " + movie_detail_arr[2]]

            movie_title_dirty = listing.find_element(By.CLASS_NAME, "styles__TitleAnchor-sc-d3de435b-9")
            movie_link = movie_title_dirty.get_attribute("href")
            try:
                movie_title = movie_title_dirty.find_element(By.TAG_NAME, "i").text
            except NoSuchElementException:
                movie_title = movie_title_dirty.text

            movie_detail_str = movie_title_dirty.text.split(" with ")
            if len(movie_detail_str) > 1 and len(movie_detail_str[1]) > 0:
                movie_notes.append("With " + movie_detail_str[1])

            movie_loc = listing.find_element(By.CLASS_NAME, "styles__VenueLocation-sc-d3de435b-14").text
            movie = MovieDescription(movie_title, movie_date, movie_time, movie_notes, movie_link, movie_loc, source="AM")
            movies.append(movie)

    driver.quit()
    return movies

def fetch_from_vt_by_date(start_date, end_date):
    movies = []
    url = f"https://www.vistatheaterhollywood.com/"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(1)
    movie_listings = driver.find_elements(By.CLASS_NAME, "shows__grid--row")
    for listing in movie_listings:
        movie_title = listing.find_element(By.TAG_NAME, "h3").text
        movie_notes = [ "In " + listing.find_element(By.CLASS_NAME, "content").find_element(By.TAG_NAME, "p").text.split(" | ")[-1].split()[0] ]
        movie_loc = "Vista Theater"
        movie_link = "https://www.vistatheaterhollywood.com/"

        try:
            movie_showings_slides = listing.find_elements(By.CLASS_NAME, "swiper-slide")
            if len(movie_showings_slides) == 0:
                movie_showings_slides = [listing.find_element(By.CLASS_NAME, "inner")]
        except NoSuchElementException:
            movie_showings_slides = [ listing.find_element(By.CLASS_NAME, "inner") ]

        movie_date_exceeds_end_date = False

        movie_date_month = listing.find_element(By.CLASS_NAME, "inner").find_element(By.CLASS_NAME, "month").get_attribute("textContent")[0:3]

        for showings_slide in movie_showings_slides:
            movie_date_index = 0
            movie_dates = showings_slide.find_elements(By.CLASS_NAME, "text__size-2")
            movie_time_clusters = showings_slide.find_elements(By.CLASS_NAME, "times")
            try:
                new_movie_date_month = showings_slide.find_element(By.CLASS_NAME, "month").get_attribute("textContent")[0:3]
            except NoSuchElementException:
                new_movie_date_month = movie_date_month

            for movie_date_dirty in movie_dates:
                movie_date = movie_date_month + f" {movie_date_dirty.get_attribute("textContent")[0:-2]}, {datetime.today().year}"

                if movie_date_month != new_movie_date_month and datetime.strptime(movie_date, "%b %d, %Y") < movies[-1].get_standardized_date():
                    movie_date_month = new_movie_date_month
                    movie_date = movie_date_month + f" {movie_date_dirty.get_attribute("textContent")[0:-2]}, {datetime.today().year}"
                    print("Switching months...")

                if datetime.strptime(movie_date, "%b %d, %Y") > end_date:
                    movie_date_exceeds_end_date = True
                    break

                if datetime.strptime(movie_date, "%b %d, %Y") < start_date:
                    continue

                for movie_time in movie_time_clusters[movie_date_index].find_elements(By.CLASS_NAME, "group"):
                    movie = MovieDescription(
                        movie_title,
                        movie_date,
                        movie_time.get_attribute("textContent").strip(),
                        movie_notes,
                        movie_link,
                        movie_loc,
                        source="VT"
                    )
                    movies.append(movie)
                movie_date_index += 1
            if movie_date_exceeds_end_date:
                break
    driver.quit()
    return movies


start_date = datetime.today()
end_date = start_date + timedelta(days=5)
movies = fetch_from_ac_by_date(start_date, end_date)
movies += fetch_from_vd_by_date(start_date, end_date)
movies += fetch_from_am_by_date(start_date, end_date)
movies += fetch_from_vt_by_date(start_date, end_date)

movies.sort()


for movie in movies:
    print(movie.to_list())
