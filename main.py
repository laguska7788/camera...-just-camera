import cv2
import mediapipe as mp
import os
import time  # Добавили для отсчёта 1.5 секунд перед закрытием

# Импортируем новый API (tasks) (разрабы чмошники удалили старыыыыыый)
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Переменные для хранения данных между кадрами
last_gesture = "None"
current_landmarks = None
dota_started = False  # Флаг, чтобы Дота не открывалась по кругу
bye_start_time = None  # Время, когда мы впервые увидели ладонь BYE


def print_result(result: mp.tasks.vision.GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    global last_gesture, current_landmarks, dota_started, bye_start_time

    if result.gestures and result.hand_landmarks:
        # Получаем стандартный жест от встроенной модели
        model_gesture = result.gestures[0][0].category_name
        current_landmarks = result.hand_landmarks[0]

        # Если мы уже в процессе закрытия от жеста BYE, приоритет ему, остальное игнорим
        if bye_start_time is not None:
            last_gesture = "Open_Palm"
            return

        # 1. ПРОВЕРКА НА СРЕДНИЙ ПАЛЕЦ (кастомная хрень т.к. гугл ленивые попы)
        # Индексы кончиков пальцев: 12 (средний), 8 (указательный), 16 (безымянный)
        # Индексы оснований пальцев: 10 (средний), 6 (указательный), 14 (безымянный)
        if (current_landmarks[12].y < current_landmarks[10].y - 0.05 and  # Средний поднят
                current_landmarks[8].y > current_landmarks[6].y and  # Указательный согнут
                current_landmarks[16].y > current_landmarks[14].y):  # Безымянный согнут

            last_gesture = "DOTA_ACTIVATED"

            if not dota_started:
                print("Жест принят! Запускаю Доту...")
                os.system("start steam://rungameid/570")
                dota_started = True

        # 2. ПРОВЕРКА НА ПОЛНОСТЬЮ РАСКРЫТУЮ ЛАДОНЬ (дефолтный знак)
        elif model_gesture == "Open_Palm":
            last_gesture = "Open_Palm"
            if bye_start_time is None:
                bye_start_time = time.time()  # Засекаем время обнаружения ладони

        # 3. ПРОВЕРКА НА ЗНАК V (дефолтный знак)
        elif model_gesture == "Victory":
            last_gesture = "Victory"
        else:
            last_gesture = "None"
    else:
        # Если рука пропала, но таймер BYE уже запущен — не сбрасываем его
        if bye_start_time is None:
            last_gesture = "None"
            current_landmarks = None


# Настраиваем нейросеть через файл-модель
options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='gesture_recognizer.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=print_result
)

# Индексы линий для отрисовки скелета руки
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

print("Программа запущенна. Доступны жесты: V, Средний палец и Ладонь (выход).")

# Инициализируем распознаватель ОДИН раз перед циклом камеры
with GestureRecognizer.create_from_options(options) as recognizer:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Зеркалим и переводим в RGB для MediaPipe
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Отправляем кадр в нейросеть
        recognizer.recognize_async(mp_image, timestamp)
        timestamp += 1

        # рисуем скелет руки с помощью opencv
        if current_landmarks:
            # Линии (зеленые палочки на вашей руке)
            for connection in HAND_CONNECTIONS:
                p1_idx, p2_idx = connection
                x1, y1 = int(current_landmarks[p1_idx].x * w), int(current_landmarks[p1_idx].y * h)
                x2, y2 = int(current_landmarks[p2_idx].x * w), int(current_landmarks[p2_idx].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Точки (красные кружочки на вашей руке)
            for landmark in current_landmarks:
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        # РЕАКЦИЯ НА ЖЕСТЫ НА ЭКРАНЕ
        if last_gesture == "Victory":
            cv2.putText(frame, "HELLO WORLD!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        elif last_gesture == "DOTA_ACTIVATED":
            cv2.putText(frame, "LAUNCHING DOTA 2...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        elif last_gesture == "Open_Palm":
            cv2.putText(frame, "BYE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)

            # Проверяем, прошло ли 1.5 секунды с момента фиксации ладони
            if bye_start_time is not None and (time.time() - bye_start_time) >= 1.5:
                print("Главное не жать на Q.")
                break

        # Выводим окно
        cv2.imshow('I SEE YOU', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print('Ну и зачем жать на это гребанное Q, когда можно показать ладошку в камеру?...')
            break

cap.release()
cv2.destroyAllWindows()