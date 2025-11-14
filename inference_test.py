#En este script vamos a hacer una prueba de inferencia con el modelo YOLO11
#la intención es ver si el modelo puede detectar objetos en un video de un dron, para posteriormente
#hacer inferencia en tiempo real con el modelo desde el video directo de un dron en tiempo real en una orange pi 5 pro.

import cv2
from ultralytics import YOLO

model = YOLO("models/Visdrone_yolo11n.pt")

RUTA_VIDEO = "Videos_test/2025_10_18_08_56_53.mp4"

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec XVID que es muy compatible
out = cv2.VideoWriter("Videos_test/2025_10_18_08_56_53_output.mp4", fourcc, 30, (640, 480))

cap = cv2.VideoCapture(RUTA_VIDEO)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.resize(frame, (640, 480))
    results = model(frame)
    annotated_frame = results[0].plot()
    out.write(annotated_frame)
    cv2.imshow("frame", frame)
    cv2.imshow("annotated_frame", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
