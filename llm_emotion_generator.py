# llm_emotion_generator.py
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Dict, List

class LLMEmotionGenerator:
    """
    Генерирует эмоциональный профиль из текста с помощью предобученной LLM.
    """
    # Маппинг выходных классов модели на наши эмоциональные переменные
    EMOTION_MAP = {
        'joy': 'joy',
        'sadness': 'sadness',
        'anger': 'anger',
        'fear': 'fear',
        'surprise': 'surprise',
        'love': 'love'   # можно использовать как compassion или любовь
    }

    # Дополнительные эмоции, которые модель не выдаёт, но мы можем задать
    # на основе комбинации или оставить нейтральными
    DEFAULT_EMOTIONS = {
        'pride': 0.2,
        'shame': 0.2,
        'guilt': 0.2,
        'disgust': 0.2,
        'compassion': 0.3,
        'hope': 0.2,
        'calmness': 0.3
    }

    def __init__(self, model_name: str = "bhadresh-savani/distilbert-base-uncased-emotion", device: str = None):
        """
        Загружает модель и токенизатор.
        :param device: 'cuda' или 'cpu'. Если None, автоопределение.
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        # Для получения вероятностей используем softmax
        self.softmax = torch.nn.Softmax(dim=1)

        # Словарь для быстрого доступа к индексам классов (зависит от модели)
        self.id2label = self.model.config.id2label  # {0: 'sadness', 1: 'joy', ...}

    def generate_emotions(self, description: str) -> Dict[str, List[float]]:
        """
        Принимает текст, возвращает словарь { 'emotion_<name>': [a, b, c] }.
        """
        # Токенизация
        inputs = self.tokenizer(description, return_tensors="pt", truncation=True, padding=True, max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = self.softmax(logits)  # shape: [1, num_classes]

        # Получаем вероятности для каждого класса
        probs = probs.cpu().numpy()[0]  # массив вероятностей

        # Строим результат
        result = {}
        for idx, prob in enumerate(probs):
            label = self.id2label[idx]  # например, 'joy'
            if label in self.EMOTION_MAP:
                emot_name = self.EMOTION_MAP[label]
                # Преобразуем вероятность в пик b (масштабируем, чтобы не было слишком низких значений)
                b = float(prob)
                # Можно применить нелинейное масштабирование: b = 0.1 + 0.8 * prob (чтобы минимум был 0.1)
                # Или оставить как есть — вероятности обычно лежат в [0,1]
                # Ограничим b от 0 до 1
                b = max(0.0, min(1.0, b))
                # Задаём a и c с небольшим запасом
                a = max(0.0, b - 0.1)
                c = min(1.0, b + 0.1)
                result[f'emotion_{emot_name}'] = [a, b, c]

        # Добавляем эмоции, которые модель не выдает, со значениями по умолчанию
        # или можно вывести их из контекста (но для простоты оставим нейтральными)
        for emot, default_val in self.DEFAULT_EMOTIONS.items():
            if f'emotion_{emot}' not in result:
                # Можно сделать их производными от основных эмоций, например, compassion = 1 - anger
                if emot == 'compassion':
                    # compassion = 1 - max(anger, fear) (пример)
                    anger = result.get('emotion_anger', [0.2,0.3,0.4])[1]
                    fear = result.get('emotion_fear', [0.2,0.3,0.4])[1]
                    b = 1.0 - max(anger, fear)
                else:
                    b = default_val
                a = max(0.0, b - 0.1)
                c = min(1.0, b + 0.1)
                result[f'emotion_{emot}'] = [a, b, c]

        return result

# Пример использования
if __name__ == "__main__":
    generator = LLMEmotionGenerator()
    text = "The agent witnesses a teenager stealing a chocolate bar in a store."
    emotions = generator.generate_emotions(text)
    for k, v in emotions.items():
        print(f"{k}: {v}")