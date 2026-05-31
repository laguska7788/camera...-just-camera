import cv2
import mediapipe as mp
import os
import time
import webbrowser

# Импортируем новый API (tasks) (разрабы чмошники удалили старыыыыыый)
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Переменные для хранения данных между кадрами
last_gesture = "None"
current_landmarks = None

# Флаги, чтобы действия не срабатывали бесконечно по кругу
dota_started = False
image_opened = False

# ТАЙМЕРЫ УДЕРЖАНИЯ (для каждого знака свой)
gesture_timers = {
    "DOTA_ACTIVATED": None,
    "Thumbs_Up": None,
    "Open_Palm": None,
    "Victory": None
}

# Сколько секунд нужно непрерывно удерживать знак (1.0 = одна секунда)
CONFIDENCE_DELAY = 1.0


def print_result(result: mp.tasks.vision.GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    global last_gesture, current_landmarks, dota_started, gesture_timers, image_opened

    if result.gestures and result.hand_landmarks:
        # Получаем стандартный жест от встроенной модели
        model_gesture = result.gestures[0][0].category_name
        current_landmarks = result.hand_landmarks[0]

        # Если мы уже запустили финальный таймер закрытия BYE, то не переключаемся
        if gesture_timers["Open_Palm"] is not None and last_gesture == "Open_Palm_CONFIRMED":
            last_gesture = "Open_Palm_CONFIRMED"
            return

        detected_now = "None"

        # 1. ПРОВЕРКА НА СРЕДНИЙ ПАЛЕЦ (кастомная хрень т.к. гугл ленивые попы)
        if (current_landmarks[12].y < current_landmarks[10].y - 0.05 and
                current_landmarks[8].y > current_landmarks[6].y and
                current_landmarks[16].y > current_landmarks[14].y):
            detected_now = "DOTA_ACTIVATED"

        # 2. ПРОВЕРКА НА ПОЛНОСТЬЮ РАСКРЫТУЮ ЛАДОНЬ (дефолтный знак)
        elif model_gesture == "Open_Palm":
            detected_now = "Open_Palm"

        # 3. я намучался нооооо проверка на лайк (все равно иногда путает кулак и лайк)
        # abs(4.x - 2.x) < 0.08 проверяет, что большой палец поднят ВЕРТИКАЛЬНО, а не завален вбок на кулаке
        elif (model_gesture == "Thumbs_Up" or
              (current_landmarks[4].y < current_landmarks[2].y - 0.05 and
               current_landmarks[4].y < current_landmarks[8].y - 0.04 and
               current_landmarks[4].y < current_landmarks[12].y - 0.04 and
               abs(current_landmarks[4].x - current_landmarks[2].x) < 0.08 and  # Палец стоит ровно вертикально
               current_landmarks[8].y > current_landmarks[6].y and
               current_landmarks[12].y > current_landmarks[10].y and
               current_landmarks[16].y > current_landmarks[14].y)):
            detected_now = "Thumbs_Up"

        # 4. ПРОВЕРКА НА ЗНАК V (дефолтный знак)
        elif model_gesture == "Victory":
            detected_now = "Victory"

        #L - логика таймеров
        current_time = time.time()

        # Сбрасываем таймеры для всех знаков, которые сейчас НЕ показываются
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

        if last_gesture != "Open_Palm_CONFIRMED":
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

cap = cv2.VideoCapture(0)
timestamp = 0

print("Программа запущенна. Требуется удержание жеста в течение 1 секунды.")

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

        #РЕАКЦИЯ НА ЖЕСТЫ НА ЭКРАНЕ
        if last_gesture.startswith("PENDING_"):
            cv2.putText(frame, "CHECKING...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 215, 255), 2)

        elif last_gesture == "Victory_CONFIRMED":
            cv2.putText(frame, "HELLO WORLD!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        elif last_gesture == "DOTA_CONFIRMED":
            cv2.putText(frame, "LAUNCHING DOTA 2...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        elif last_gesture == "Thumbs_Up_CONFIRMED":
            cv2.putText(frame, "OPENING IMAGE...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)

        elif last_gesture == "Open_Palm_CONFIRMED":
            cv2.putText(frame, "BYE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            if gesture_timers["Open_Palm"] is not None and (time.time() - gesture_timers["Open_Palm"]) >= (
                    CONFIDENCE_DELAY + 1.5):
                print("Выход из программы по жесту.")
                break

        cv2.imshow('I SEE YOU', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()