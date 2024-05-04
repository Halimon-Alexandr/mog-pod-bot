from modules.schedule import workday, weekend, bus_arrival_times, special_holidays, holiday
import pytz
from datetime import datetime, date, timedelta

kiev_timezone = pytz.timezone("Europe/Kiev")


class Searcher:
    """
    This class includes methods for navigating through the bus schedule ('next' and 'previous') and searching for bus information based on the provided parameters ('find').
    The class also tracks user activity, including the number of interaction_count and the timestamp of the last visit.
    The bus schedule is determined based on the current day, and the result string is formatted with relevant information about the next scheduled bus.
    """

    workday_schedule = sorted(workday)
    weekend_schedule = sorted(weekend)
    holidays_schedule = sorted(holiday)
    special_holidays = special_holidays
    bus_arrival_times = bus_arrival_times
    interaction_count = 0
    last_visit = None
    search_query = ""
    offset = 0

    def __init__(self, username=None):
        if username is None:
            self.username = "Без імені"
        else:
            self.username = username


    def load_schedule(self):
        today = datetime.now(kiev_timezone).date()
        # Перевіряємо, чи сьогоднішній день є в списку святкових днів
        if today in self.special_holidays:
            return self.holidays_schedule
        # Перевіряємо, чи це будній день
        weekday = today.weekday()
        is_workday = weekday < 5
        # Вибираємо графік залежно від того, чи це будній день
        bus_schedule = self.workday_schedule if is_workday else self.weekend_schedule

        return bus_schedule


    def bus_schedule_generator(self):
        """Generate bus schedule information based on the current day of the week (workday or weekend) and the provided bus arrival times."""
        index = 0
        skip_stops = {
            "Ощадбанк",
            "Монтажний технікум",
            "Машинобудівний завод",
            "Школа № 5",
            "Лікарня",
            "Верхня Немія",
            "Залізничний вокзал",
            "Маслозавод",
            "Автовокзал",
            "Школа № 2",
        }
        change_bus = True
        
        bus_schedule = self.load_schedule()
        while len(bus_schedule) != index:
            try:
                current_time = bus_schedule[index]

                for direction, offset in self.bus_arrival_times.get(
                    self.search_query, {}
                ).items():
                    departure_time = bus_schedule[index]
                    bus_number = (index % 2) + 1
                    departure_time_dt = datetime.now(kiev_timezone).replace(
                        hour=int(departure_time[:2]),
                        minute=int(departure_time[3:]),
                        second=0,
                    )
                    arrival_time = departure_time_dt + timedelta(minutes=offset)
                    if self.search_query in skip_stops and change_bus:
                        index += 1
                        change_bus = False

                    yield direction, bus_number, arrival_time
                index += 1
                change_bus = True
            except IndexError:
                break

    def find(self, bus_stop_name=None, current_time=None):
        """
        Search for bus information based on the provided bus stop name and current time.

        Args:
        - bus_stop_name (str): The name of the bus stop to search for. If not provided, the last searched bus stop will be used.
        - current_time (datetime): The current time to use for the search. If not provided, the current system time will be used.

        Returns:
        - str: A formatted string containing information about the next scheduled bus arrival at the specified bus stop.
        - types.ReplyKeyboardbuttons_texts: A keyboard buttons_texts with navigation buttons for interacting with the bot.
        """
        # Update the last visit timestamp
        self.last_visit = datetime.now(kiev_timezone)
        # Updating the number of interaction_count
        self.interaction_count += 1
        # Set default values for bus_stop_name and current_time if not provided
        if current_time is None:
            current_time = self.last_visit
        if bus_stop_name is None:
            bus_stop_name = self.search_query
        # Iterate through the base schedule to find the requested bus stop
        found_stops = []
        for current_bus_stop, _ in self.bus_arrival_times.items():
            if bus_stop_name.lower() in current_bus_stop.lower():
                found_stops.append(current_bus_stop)
        if len(found_stops) == 1:
            self.search_query = found_stops[0]
            result = f"🚏 {found_stops[0]}."
        elif len(found_stops) > 1:
            buttons_texts = found_stops
            return (
                "За вашим  запитом знайдено декілька зупинок, \nбудь ласка, оберіть потрібну з нижче наведених",
                buttons_texts,
            )
        else:
            buttons_texts = ["Пошук 🔎", "Список 📖", "Допомога 🙋"]
            return (
                "Вибачте, за вашим запитом не знайдено жодної із зупинок. \nБудь ласка, перевірте правильність написання назви або спробуйте знайти потрібне, нажавши кнопку  'Список 📖'",
                buttons_texts,
            )
        schedule_current_busstop = list(self.bus_schedule_generator())
        schedule_current_busstop = sorted(
            schedule_current_busstop, key=lambda item: item[2]
        )
        for index, (direction, bus_number, arrival_time) in enumerate(
            schedule_current_busstop
        ):
            if current_time.time() <= arrival_time.time():
                next_bus_info = schedule_current_busstop[
                    (index + self.offset) % len(schedule_current_busstop)
                ]
                direction = next_bus_info[0]
                bus_number = next_bus_info[1]
                arrival_time = next_bus_info[2]

                # Розрахунок часу залишку
                time_left = arrival_time - datetime.now(kiev_timezone)
                hours_left = time_left.seconds // 3600
                minutes_left = (time_left.seconds % 3600) // 60

                # Додання інформації про час залишку до результату
                result += f"\n👉 В напрямку {direction}"
                result += f"\n🚌 № {bus_number}, ⌚ о {arrival_time.strftime('%H:%M')}"
                result += (
                    f"\nЧерез {hours_left} годин {minutes_left} хвилин\n"
                    if hours_left
                    else f"\nЧерез {minutes_left} хвилин\n"
                )
                break

            # If no bus information was added, perform a search starting from midnight
        if result == f"🚏 {self.search_query}.":
            return self.find(
                current_time=datetime.now(kiev_timezone).replace(
                    hour=0, minute=0, second=0
                )
            )
        buttons_texts = [
            "🔼 Попередній",
            "▶\nОновити",
            "🔽 Наступний",
            "👉Основне меню👈",
        ]
        return result, buttons_texts
