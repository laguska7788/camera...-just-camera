import cv2
import mediapipe as mp
import os
import time
import webbrowser
from datetime import datetime
import math
import pygame

# Импортируем новый API (tasks) (разрабы чмошники удалили старыыыыыый)
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Инициализируем аудио-микшер pygame
pygame.mixer.init()

# Переменные для хранения данных между кадрами
last_gesture = "None"
current_landmarks = None

# Флаги, чтобы действия не срабатывали бесконечно по кругу
dota_started = False
image_opened = False
music_started = False  # Флаг для музыки

# ТАЙМЕРЫ УДЕРЖАНИЯ
gesture_timers = {
    "DOTA_ACTIVATED": None,
    "Thumbs_Up": None,
    "Open_Palm": None,
    "Victory": None,
    "OK_Gesture": None,
    "ILoveYou": None,
    "Closed_Fist": None
}

# Сколько секунд нужно непрерывно удерживать знак (1.0 = одна секунда)
CONFIDENCE_DELAY = 1.0


def print_result(result: mp.tasks.vision.GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    global last_gesture, current_landmarks, dota_started, gesture_timers, image_opened, music_started

    if result.gestures and result.hand_landmarks:
        # Получаем стандартный жест от встроенной модели
        model_gesture = result.gestures[0][0].category_name
        current_landmarks = result.hand_landmarks[0]

        detected_now = "None"

        # Считаем расстояние между кончиком большого (4) и указательного (8) для жеста ОК
        dist_thumb_index = math.sqrt(
            (current_landmarks[4].x - current_landmarks[8].x) ** 2 +
            (current_landmarks[4].y - current_landmarks[8].y) ** 2
        )

        # 1. ПРОВЕРКА НА СРЕДНИЙ ПАЛЕЦ (кастомная хрень т.к. гугл ленивые попы)
        if (current_landmarks[12].y < current_landmarks[10].y - 0.05 and
                current_landmarks[8].y > current_landmarks[6].y and
                current_landmarks[16].y > current_landmarks[14].y):
            detected_now = "DOTA_ACTIVATED"

        # 2. ПРОВЕРКА НА ПОЛНОСТЬЮ РАСКРЫТУЮ ЛАДОНЬ (дефолтный знак)
        elif model_gesture == "Open_Palm":
            detected_now = "Open_Palm"

        # 3. ИСПРАВЛЕННАЯ СВЕРХТОЧНАЯ ПРОВЕРКА НА КУЛАК (✊)
        # Мы добавили проверку: кончик большого пальца (4) ДОЛЖЕН быть ниже или на уровне сустава указательного (6).
        # Если большой палец поднят вверх (как на фото боком), это условие больше не сработает!
        elif (model_gesture == "Closed_Fist" or
              (current_landmarks[8].y > current_landmarks[6].y and
               current_landmarks[12].y > current_landmarks[10].y and
               current_landmarks[16].y > current_landmarks[14].y and
               current_landmarks[20].y > current_landmarks[18].y and
               current_landmarks[4].y > current_landmarks[6].y - 0.02)):
            detected_now = "Closed_Fist"

        # 4. ПРОКАЧАННАЯ СТРОГАЯ ПРОВЕРКА НА ЛАЙК
        # Теперь лайк боком у подбородка идеально залетает сюда
        elif (model_gesture == "Thumbs_Up" or
              (current_landmarks[4].y < current_landmarks[2].y - 0.05 and
               current_landmarks[4].y < current_landmarks[8].y - 0.04 and
               current_landmarks[4].y < current_landmarks[12].y - 0.04 and
               abs(current_landmarks[4].x - current_landmarks[2].x) < 0.08 and
               current_landmarks[8].y > current_landmarks[6].y and
               current_landmarks[12].y > current_landmarks[10].y and
               current_landmarks[16].y > current_landmarks[14].y)):
            detected_now = "Thumbs_Up"

        # 5. КАСТOMНАЯ ПРОВЕРКА НА ЖЕСТ ОК (👌)
        elif dist_thumb_index < 0.045 and current_landmarks[12].y < current_landmarks[10].y:
            detected_now = "OK_Gesture"

        # 6. ВСТРОЕННЫЙ ЖЕСТ I LOVE YOU (🤟) — ВКЛЮЧЕНИЕ МУЗЫКИ
        elif model_gesture == "ILoveYou":
            detected_now = "ILoveYou"

        # 7. ПРОВЕРКА НА ЗНАК V (дефолтный знак)
        elif model_gesture == "Victory":
            detected_now = "Victory"

        # --- ЛОГИКА ТАЙМЕРОВ ---
        current_time = time.time()

        # Сбрасываем таймеры для всех знаков, которые СЕЙЧАС НЕ показываются
        for gesture_name in gesture_timers.keys():
            if gesture_name != detected_now:
                gesture_timers[gesture_name] = None

        if detected_now != "None":
            if gesture_timers[detected_now] is None:
                gesture_timers[detected_now] = current_time

            elapsed = current_time - gesture_timers[detected_now]

            if elapsed >= CONFIDENCE_DELAY:
                if detected_now == "DOTA_ACTIVATED":
                    last_gesture = "DOTA_CONFIRMED"
                    if not dota_started:
                        print("Жест зафиксирован 1 сек! Запускаю Доту...")
                        os.system("start steam://rungameid/570")
                        dota_started = True

                elif detected_now == "Thumbs_Up":
                    last_gesture = "Thumbs_Up_CONFIRMED"
                    if not image_opened:
                        print("Лайк зафиксирован 1 сек! Открываю картинку...")
                        url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRll0etFawd8OYQNWE9Sodr2wx0x1SKfoatwA&s"
                        webbrowser.open(url)
                        image_opened = True

                elif detected_now == "Open_Palm":
                    last_gesture = "Open_Palm_CONFIRMED"

                elif detected_now == "OK_Gesture":
                    last_gesture = "OK_CONFIRMED"

                elif detected_now == "ILoveYou":
                    last_gesture = "ILY_CONFIRMED"
                    if not music_started:
                        print("Жест ILY зафиксирован 1 сек! Включаю встроенную музыку...")
                        try:
                            pygame.mixer.music.load("music.mp3")
                            pygame.mixer.music.play()
                            music_started = True
                        except Exception as e:
                            print(f"Ошибка воспроизведения файла music.mp3: {e}")
                            music_started = True

                elif detected_now == "Closed_Fist":
                    last_gesture = "FIST_CONFIRMED"
                    pygame.mixer.music.stop()
                    music_started = False

                elif detected_now == "Victory":
                    if last_gesture != "Victory_CONFIRMED":
                        print("Hello World!")
                    last_gesture = "Victory_CONFIRMED"
            else:
                last_gesture = f"PENDING_{detected_now}"
        else:
            last_gesture = "None"
            image_opened = False

    else:
        for gesture_name in gesture_timers.keys():
            gesture_timers[gesture_name] = None

        last_gesture = "None"
        current_landmarks = None
        image_opened = False


# Настраиваем нейросеть
options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='gesture_recognizer.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=print_result
)

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17)
]

DAYS_RU = {
    "Monday": "Ponedelnik", "Tuesday": "Vtornik", "Wednesday": "Sreda",
    "Thursday": "Chetverg", "Friday": "Pyatnica", "Saturday": "Subbota", "Sunday": "Voskresenye"
}

cap = cv2.VideoCapture(0)
timestamp = 0

print("Программа запущенна. Доступны жесты: V, Средний палец, Ладонь, Лайк, ОК, ILY и Кулак.")

with GestureRecognizer.create_from_options(options) as recognizer:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        recognizer.recognize_async(mp_image, timestamp)
        timestamp += 1

        # Отрисовка скелета руки
        if current_landmarks:
            for connection in HAND_CONNECTIONS:
                p1_idx, p2_idx = connection
                x1, y1 = int(current_landmarks[p1_idx].x * w), int(current_landmarks[p1_idx].y * h)
                x2, y2 = int(current_landmarks[p2_idx].x * w), int(current_landmarks[p2_idx].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            for landmark in current_landmarks:
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        # --- РЕАКЦИЯ НА ЖЕСТЫ НА ЭКРАНЕ ---
        if last_gesture.startswith("PENDING_"):
            cv2.putText(frame, "CHECKING...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 215, 255), 2)

        elif last_gesture == "Victory_CONFIRMED":
            cv2.putText(frame, "HELLO WORLD!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        elif last_gesture == "DOTA_CONFIRMED":
            cv2.putText(frame, "LAUNCHING DOTA 2...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        elif last_gesture == "Thumbs_Up_CONFIRMED":
            cv2.putText(frame, "OPENING IMAGE...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)

        elif last_gesture == "OK_CONFIRMED":
            now = datetime.now()
            date_str = now.strftime("%d.%m.%Y")
            day_of_week = DAYS_RU.get(now.strftime("%A"), now.strftime("%A"))
            time_str = now.strftime("%H:%M")

            cv2.putText(frame, f"Date: {date_str}", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 150), 2)
            cv2.putText(frame, f"Day:  {day_of_week}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 150), 2)
            cv2.putText(frame, f"Time: {time_str}", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 255), 3)

        elif last_gesture == "ILY_CONFIRMED":
            cv2.putText(frame, "PLAYING MUSIC...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

        elif last_gesture == "FIST_CONFIRMED":
            cv2.putText(frame, "MUSIC STOPPED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        elif last_gesture == "Open_Palm_CONFIRMED":
            cv2.putText(frame, "BYE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            if gesture_timers["Open_Palm"] is not None and (time.time() - gesture_timers["Open_Palm"]) >= (
                    CONFIDENCE_DELAY + 1.5):
                print("Жест удержан. Выход из программы.")
                break

        cv2.imshow('I SEE YOU', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()