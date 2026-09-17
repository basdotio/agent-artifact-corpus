---
name: artificial-intelligence-engineer
description: Ingeniero Especialista en IA con expertise en NLP/NLU, construcción de modelos desde cero, fine-tuning avanzado, capas personalizadas con Keras/TensorFlow, y adaptación de modelos preentrenados. **Cuándo usar**: arquitectura de modelos de lenguaje, fine-tuning de BERT/transformers, construcción de capas custom, experimentos con arquitecturas nuevas, optimización de hiperparámetros, e implementación de pipelines NLP end-to-end.
---

## Descripción General

Esta skill empodera al agente para actuar como **Ingeniero Especialista en IA** para proyectos de NLP/NLU en contextos de clasificación de texto y análisis de experiencias turísticas. Proporciona expertise en:

- **Construcción de modelos NLP/NLU**: clasificación de texto, detección de intents, análisis de sentimiento, categorización de sugerencias vs críticas
- **Fine-tuning de transformers**: adaptar modelos preentrenados (BERT, ALBERT, RoBERTa, DistilBERT) a dominios específicos
- **Arquitecturas personalizadas**: capas custom en Keras/TensorFlow, modelos secuenciales, modelos funcionales, arquitecturas híbridas
- **Modelos desde cero**: implementar regresión logística, redes neuronales básicas, RNNs, LSTMs, GRUs, Transformers simplificados
- **Modelos preentrenados**: descargar, adaptar, fine-tunear modelos de Hugging Face, OpenAI, etc.
- **Optimización y evaluación**: métricas de clasificación, validación cruzada, grid search, calibración de modelos
- **Producción y despliegue**: serializar modelos, crear pipelines reproducibles, exportar a formatos estándar

---

## Cuándo Invocar Esta Skill

Usa esta skill cuando el usuario o task pida:
- "Construye un modelo de clasificación para detectar sugerencias en comentarios" → Modelo custom + fine-tuning
- "Fine-tunea BERT para clasificación binaria de críticas vs sugerencias" → Fine-tuning avanzado
- "Crea capas personalizadas en Keras para un modelo multi-tarea" → Capas custom + arquitectura
- "Convierte un modelo preentrenado en un clasificador de experencias turísticas" → Adaptation + tuning
- "Implementa un modelo Transformer desde cero para NLU" → Arquitectura desde cero
- "Optimiza hiperparámetros de mi modelo de sentimientos" → Grid search + evaluación
- "Exporta el modelo entrenado para producción" → Serialización + deployment

---

### Verificar Prerequisites (Comandos para el usuario)

```bash
# Comprobar Python
python3 --version

# Instalar librerías principales
pip install tensorflow transformers torch scikit-learn numpy pandas matplotlib seaborn

# Verificar TensorFlow
python3 -c "import tensorflow as tf; print(tf.__version__)"

# Comprobar GPU (opcional)
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

# Descargar modelo preentrenado de prueba
python3 -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('bert-base-uncased')"
```

---

## Flujo de Trabajo Fase por Fase

### Fase 1: Definición del Problema y Dataset

Cuando se inicia una tarea de IA:

1. **Entender el objetivo:**
   - ¿Clasificación o regressión? (ej: clasificación binaria: sugerencia vs no sugerencia)
   - ¿Multiclase o multilabel? (ej: sugerencia, crítica, opinión, etc)
   - ¿QUE métrica importa más? (precisión, recall, F1, AUC)

2. **Explorar dataset:**
   ```python
   import pandas as pd
   from collections import Counter
   
   df = pd.read_csv('data_analysis/data/Chile_all1_part1.csv')
   
   # Distribución de clases
   print(df['class_label'].value_counts())
   
   # Ejemplos por clase
   for cls in df['class_label'].unique():
       sample = df[df['class_label'] == cls].iloc[0]['comment']
       print(f"\n{cls}: {sample[:200]}")
   ```

3. **Definir split de datos:**
   ```python
   from sklearn.model_selection import train_test_split
   
   X_train, X_test, y_train, y_test = train_test_split(
       df['comment'], df['class_label'],
       test_size=0.2, random_state=42, stratify=df['class_label']
   )
   
   print(f"Train: {len(X_train)}, Test: {len(X_test)}")
   print(f"Distribución train:\n{y_train.value_counts()}")
   ```

### Fase 2: Selección de Arquitectura

**Opciones por complejidad:**

| Caso | Arquitectura | Ventajas | Desventajas |
|------|-------------|----------|------------|
| Baseline simple | Regresión logística + TF-IDF | Rápido, interpretable, sin GPU | Baja precisión, no captura semántica |
| Texto corto, datos limitados | Dense NN (2-3 capas) | Entrenable en CPU, rápido | Limitada en contexto largo |
| Datos medianos, texto complejo | LSTM/GRU + embeddings | Captura secuencias, buena precisión | Más lento, requiere tuning |
| Datos grandes, SOTA | BERT/RoBERTa fine-tuned | SOTA accuracy, transfer learning | Requiere GPU, lento |
| Producción con limite recursos | DistilBERT/ALBERT fine-tuned | Balanceado: precisión + velocidad | Tradeoff en accuracy vs speed |

**Recomendación para este proyecto (comentarios TripAdvisor):**
- **MVP**: Dense NN + GloVe embeddings
- **Producción**: DistilBERT fine-tuned con capas custom
- **SOTA**: BERT-base o RoBERTa fine-tuned

### Fase 3: Preparación de Datos

**Tokenización y Encoding Estándar:**

```python
from transformers import AutoTokenizer
import numpy as np

# Opción A: Usar tokenizer de Hugging Face
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')

def tokenize_texts(texts, max_length=128):
    encodings = tokenizer(
        texts.tolist(),
        truncation=True,
        max_length=max_length,
        padding='max_length',
        return_tensors='tf'
    )
    return encodings

# Opción B: Tokenización manual (para modelos custom)
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

tokenizer_manual = Tokenizer(num_words=5000)
tokenizer_manual.fit_on_texts(X_train.tolist())

X_train_seq = tokenizer_manual.texts_to_sequences(X_train.tolist())
X_train_pad = pad_sequences(X_train_seq, maxlen=128)

X_test_seq = tokenizer_manual.texts_to_sequences(X_test.tolist())
X_test_pad = pad_sequences(X_test_seq, maxlen=128)

print(f"X_train shape: {X_train_pad.shape}")  # (N, 128)
```

**Preparación de Labels:**

```python
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.utils import to_categorical

# Codificar labels a integers
le = LabelEncoder()
y_train_encoded = le.fit_transform(y_train)
y_test_encoded = le.transform(y_test)

# Si es multiclase, convertir a one-hot
y_train_categorical = to_categorical(y_train_encoded)
y_test_categorical = to_categorical(y_test_encoded)

print(f"Clases: {le.classes_}")
print(f"y_train shape: {y_train_categorical.shape}")
```

---

## Fase 4: Construcción de Modelos Desde Cero

### 4.1 Modelo Baseline: Regresión Logística

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Crear pipeline
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
    ('clf', LogisticRegression(max_iter=1000, random_state=42))
])

# Entrenar
pipeline.fit(X_train, y_train)

# Evaluar
from sklearn.metrics import classification_report, confusion_matrix
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred))
```

### 4.2 Red Neuronal Densa Custom

```python
import tensorflow as tf
from tensorflow.keras import layers, Sequential
from tensorflow.keras.embeddings import Embedding

# Opción A: Modelo Secuencial Simple
model_dense = Sequential([
    layers.Embedding(input_dim=5000, output_dim=128, input_length=128),
    layers.GlobalAveragePooling1D(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(num_classes, activation='softmax')  # Clasificación multiclase
])

model_dense.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model_dense.summary()

# Entrenar
history = model_dense.fit(
    X_train_pad, y_train_categorical,
    epochs=10,
    batch_size=32,
    validation_split=0.2,
    verbose=1
)
```

### 4.3 LSTM/GRU Custom para Secuencias

```python
model_lstm = Sequential([
    layers.Embedding(input_dim=5000, output_dim=128, input_length=128),
    layers.LSTM(64, return_sequences=True),
    layers.Dropout(0.3),
    layers.LSTM(32),
    layers.Dropout(0.2),
    layers.Dense(64, activation='relu'),
    layers.Dense(num_classes, activation='softmax')
])

model_lstm.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
)

history = model_lstm.fit(
    X_train_pad, y_train_categorical,
    epochs=15,
    batch_size=32,
    validation_split=0.2,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
    ],
    verbose=1
)
```

### 4.4 Modelo Funcional Custom (Multi-Input)

```python
# Modelo con entrada doble: comentario + metadata
text_input = layers.Input(shape=(128,), name='text')
metadata_input = layers.Input(shape=(3,), name='metadata')  # [rating, length, language_encoded]

# Rama de texto
x_text = layers.Embedding(5000, 128)(text_input)
x_text = layers.LSTM(64)(x_text)
x_text = layers.Dense(32, activation='relu')(x_text)

# Rama de metadata
x_meta = layers.Dense(16, activation='relu')(metadata_input)

# Fusionar
merged = layers.Concatenate()([x_text, x_meta])
output = layers.Dense(64, activation='relu')(merged)
output = layers.Dense(num_classes, activation='softmax')(output)

model_functional = tf.keras.Model(
    inputs=[text_input, metadata_input],
    outputs=output,
    name='MultiInputClassifier'
)

model_functional.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Entrenar
history = model_functional.fit(
    {'text': X_train_pad, 'metadata': X_train_metadata},
    y_train_categorical,
    epochs=10,
    batch_size=32,
    validation_split=0.2,
    verbose=1
)
```

---

## Fase 5: Capas Personalizadas con Keras

### 5.1 Custom Layer: Attention Mechanism

```python
class AttentionLayer(layers.Layer):
    def __init__(self, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)
    
    def build(self, input_shape):
        # input_shape: (batch_size, sequence_length, embedding_dim)
        self.W = self.add_weight(
            name='attention_weight',
            shape=(input_shape[-1], 1),
            initializer='glorot_uniform',
            trainable=True
        )
        super(AttentionLayer, self).build(input_shape)
    
    def call(self, x):
        # Calcular attention scores
        scores = tf.nn.softmax(tf.keras.backend.dot(x, self.W), axis=1)
        # Aplicar weights
        context = tf.reduce_sum(x * scores, axis=1)
        return context
    
    def get_config(self):
        return super().get_config()

# Usar la capa custom
model_with_attention = Sequential([
    layers.Embedding(5000, 128, input_length=128),
    layers.LSTM(64, return_sequences=True),
    AttentionLayer(),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(num_classes, activation='softmax')
])

model_with_attention.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)
```

### 5.2 Custom Layer: Feature Extraction

```python
class CustomFeatureLayer(layers.Layer):
    def __init__(self, units=64, **kwargs):
        super(CustomFeatureLayer, self).__init__(**kwargs)
        self.units = units
    
    def build(self, input_shape):
        self.dense1 = layers.Dense(self.units, activation='relu')
        self.bn = layers.BatchNormalization()
        self.dense2 = layers.Dense(self.units // 2, activation='relu')
        super(CustomFeatureLayer, self).build(input_shape)
    
    def call(self, x, training=False):
        x = self.dense1(x)
        x = self.bn(x, training=training)
        x = self.dense2(x)
        return x
    
    def get_config(self):
        config = super().get_config()
        config.update({'units': self.units})
        return config

# Usar
model = Sequential([
    layers.Embedding(5000, 128, input_length=128),
    layers.LSTM(64),
    CustomFeatureLayer(units=128),
    layers.Dropout(0.2),
    layers.Dense(num_classes, activation='softmax')
])
```

---

## Fase 6: Fine-Tuning de Modelos Preentrenados

### 6.1 Fine-Tuning de BERT Básico

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import tensorflow as tf

# Descargar modelo y tokenizer
model_name = 'bert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=num_classes  # ej: 2 (sugerencia vs no), 3 (sugerencia, crítica, opinión)
)

# Tokenizar dataset
def preprocess_function(texts, labels):
    encodings = tokenizer(
        texts.tolist(),
        truncation=True,
        max_length=128,
        padding='max_length',
        return_tensors='tf'
    )
    return encodings, labels

X_train_encoded, y_train_tf = preprocess_function(X_train, y_train_encoded)
X_val_encoded, y_val_tf = preprocess_function(X_val, y_val_encoded)

# Crear TF Dataset
train_dataset = tf.data.Dataset.from_tensor_slices((
    dict(X_train_encoded),
    y_train_tf
)).batch(32).shuffle(1000)

val_dataset = tf.data.Dataset.from_tensor_slices((
    dict(X_val_encoded),
    y_val_tf
)).batch(32)

# Compilar y entrenar
optimizer = tf.keras.optimizers.Adam(learning_rate=2e-5)
model.compile(optimizer=optimizer)

model.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=3
)
```

### 6.2 Fine-Tuning Avanzado con Capas Custom

```python
from transformers import TFAutoModel

# Cargar base BERT (sin cabeza de clasificación)
base_model = TFAutoModel.from_pretrained('bert-base-uncased')

# Congelar capas base iniciales
for i, layer in enumerate(base_model.layers):
    if i < len(base_model.layers) - 4:  # Congelar últimas 4 capas
        layer.trainable = False

# Construir modelo custom con capas adicionales
input_ids = layers.Input(shape=(128,), dtype=tf.int32, name='input_ids')
attention_mask = layers.Input(shape=(128,), dtype=tf.int32, name='attention_mask')

# BERT base
x = base_model(input_ids=input_ids, attention_mask=attention_mask)[1]  # [CLS] token

# Capas custom
x = layers.Dropout(0.2)(x)
x = layers.Dense(256, activation='relu')(x)
x = layers.BatchNormalization()(x)
x = layers.Dropout(0.2)(x)
x = layers.Dense(128, activation='relu')(x)
output = layers.Dense(num_classes, activation='softmax')(x)

model_finetuned = tf.keras.Model(
    inputs=[input_ids, attention_mask],
    outputs=output
)

model_finetuned.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=2e-5),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Entrenar
history = model_finetuned.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=5,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
    ]
)
```

### 6.3 Fine-Tuning de DistilBERT (Modelo Ligero)

```python
# DistilBERT es 40% más pequeño y 60% más rápido que BERT
model_name = 'distilbert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(model_name)
base_model = TFAutoModel.from_pretrained(model_name)

# Similar al proceso anterior, pero más rápido en entrenamiento
# ... (misma estructura que BERT)
```

---

## Fase 7: Transfer Learning y Adaptación

### 7.1 Cargar Modelo Preentrenado y Añadir Capas

```python
# Cargar modelo completo preentrenado
pretrained_model = tf.keras.models.load_model('path/to/pretrained_model.h5')

# Congelar capas de feature extraction
for layer in pretrained_model.layers[:-3]:
    layer.trainable = False

# Añadir capas custom al final
model_adapted = tf.keras.Sequential(
    pretrained_model.layers[:-1] +  # Todas menos la última
    [
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation='softmax')
    ]
)

model_adapted.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Entrenar solo las nuevas capas
history = model_adapted.fit(
    X_train_pad, y_train_categorical,
    epochs=5,
    batch_size=32,
    validation_split=0.2
)

# Descongelar algunas capas y fine-tunear
for layer in model_adapted.layers[-10:]:
    layer.trainable = True

model_adapted.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

history2 = model_adapted.fit(
    X_train_pad, y_train_categorical,
    epochs=5,
    batch_size=32,
    validation_split=0.2
)
```

---

## Fase 8: Evaluación y Optimización

### 8.1 Métricas Completas

```python
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, auc, precision_recall_curve, f1_score
)

# Hacer predicciones
y_pred_proba = model.predict(X_test_pad)
y_pred = np.argmax(y_pred_proba, axis=1)

# Reportes
print(classification_report(y_test_encoded, y_pred, target_names=le.classes_))
print(f"\nMatriz de Confusión:\n{confusion_matrix(y_test_encoded, y_pred)}")
print(f"F1-Score: {f1_score(y_test_encoded, y_pred, average='weighted'):.4f}")

# ROC-AUC (para binaria)
if num_classes == 2:
    auc_score = roc_auc_score(y_test_encoded, y_pred_proba[:, 1])
    print(f"ROC-AUC: {auc_score:.4f}")
```

### 8.2 Visualización de Resultados

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Curva de entrenamiento
axes[0, 0].plot(history.history['loss'], label='Train Loss')
axes[0, 0].plot(history.history['val_loss'], label='Val Loss')
axes[0, 0].set_title('Loss Over Epochs')
axes[0, 0].legend()

axes[0, 1].plot(history.history['accuracy'], label='Train Acc')
axes[0, 1].plot(history.history['val_accuracy'], label='Val Acc')
axes[0, 1].set_title('Accuracy Over Epochs')
axes[0, 1].legend()

# 2. Matriz de confusión
sns.heatmap(confusion_matrix(y_test_encoded, y_pred), 
            annot=True, fmt='d', ax=axes[1, 0], cmap='Blues')
axes[1, 0].set_title('Confusion Matrix')

# 3. Classification report como tabla
from sklearn.metrics import precision_recall_fscore_support
precision, recall, f1, _ = precision_recall_fscore_support(
    y_test_encoded, y_pred, average=None
)

x_pos = np.arange(len(le.classes_))
width = 0.25
axes[1, 1].bar(x_pos - width, precision, width, label='Precision')
axes[1, 1].bar(x_pos, recall, width, label='Recall')
axes[1, 1].bar(x_pos + width, f1, width, label='F1')
axes[1, 1].set_xticks(x_pos)
axes[1, 1].set_xticklabels(le.classes_)
axes[1, 1].set_title('Metrics by Class')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('data_analysis/model_evaluation.png', dpi=300, bbox_inches='tight')
plt.close()
```

### 8.3 Grid Search para Hiperparámetros

```python
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC

# Para modelos sklearn
param_grid = {
    'C': [0.1, 1, 10],
    'kernel': ['linear', 'rbf'],
    'gamma': ['scale', 'auto']
}

svm_model = GridSearchCV(
    SVC(probability=True),
    param_grid,
    cv=5,
    scoring='f1_weighted'
)

svm_model.fit(X_train_tfidf, y_train)
print(f"Best params: {svm_model.best_params_}")
print(f"Best CV score: {svm_model.best_score_:.4f}")
```

---

## Fase 9: Serialización y Despliegue

### 9.1 Guardar Modelos

```python
# Guardar modelo Keras completo
model.save('models/pytorch_classifier_v1.h5')
model.save('models/pytorch_classifier_v1')  # SavedModel format

# Guardar modelo TensorFlow Lite (móvil)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('models/pytorch_classifier_v1.tflite', 'wb') as f:
    f.write(tflite_model)

# Guardar tokenizer y encoder
import pickle
with open('models/tokenizer.pkl', 'wb') as f:
    pickle.dump(tokenizer_manual, f)
with open('models/label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)
```

### 9.2 Cargar y Usar Modelo Guardado

```python
import pickle

# Cargar modelo
loaded_model = tf.keras.models.load_model('models/pytorch_classifier_v1.h5')

# Cargar tokenizer y encoder
with open('models/tokenizer.pkl', 'rb') as f:
    tokenizer = pickle.load(f)
with open('models/label_encoder.pkl', 'rb') as f:
    le = pickle.load(f)

# Hacer predicción en texto nuevo
new_text = "Excelente servicio, muy recomendado"
seq = tokenizer.texts_to_sequences([new_text])
padded = pad_sequences(seq, maxlen=128)
prediction = loaded_model.predict(padded)
predicted_class = le.inverse_transform([np.argmax(prediction)])
confidence = np.max(prediction)

print(f"Clase: {predicted_class[0]}, Confianza: {confidence:.4f}")
```

### 9.3 Pipeline de Producción

```python
class TextClassificationPipeline:
    def __init__(self, model_path, tokenizer_path, encoder_path):
        self.model = tf.keras.models.load_model(model_path)
        with open(tokenizer_path, 'rb') as f:
            self.tokenizer = pickle.load(f)
        with open(encoder_path, 'rb') as f:
            self.le = pickle.load(f)
    
    def preprocess(self, text):
        # Limpiar y normalizar
        text = text.lower().strip()
        seq = self.tokenizer.texts_to_sequences([text])
        padded = pad_sequences(seq, maxlen=128)
        return padded
    
    def predict(self, text):
        X = self.preprocess(text)
        logits = self.model.predict(X, verbose=0)
        prediction = np.argmax(logits, axis=1)[0]
        confidence = np.max(logits)
        class_name = self.le.inverse_transform([prediction])[0]
        return {'class': class_name, 'confidence': float(confidence)}
    
    def predict_batch(self, texts):
        results = [self.predict(text) for text in texts]
        return results

# Uso
pipeline = TextClassificationPipeline(
    'models/pytorch_classifier_v1.h5',
    'models/tokenizer.pkl',
    'models/label_encoder.pkl'
)

result = pipeline.predict("Magnífico hotel, muy buena atención")
print(result)  # {'class': 'sugerencia', 'confidence': 0.92}
```

---

## Checklist de Modelo Completado

Antes de marcar una tarea de IA como completada:

- [ ] Dataset explorado: distribución de clases balanceada (si es necesario)
- [ ] Preprocesamiento definido: tokenización, padding, normalización
- [ ] Split train/val/test realizado (70/15/15 o 80/20)
- [ ] Modelo baseline entrenado y evaluado
- [ ] Hiperparámetros optimizados (lr, batch_size, epochs)
- [ ] Modelo principal (SOTA) entrenado sin overfitting
- [ ] Evaluación completa: precision, recall, F1, confusion matrix, ROC-AUC
- [ ] Análisis de errores: casos fallidos documentados
- [ ] Modelo guardado en formato estándar (.h5, .pb, o .safetensors)
- [ ] Pipeline de inferencia probado con datos nuevos
- [ ] Reporteejecutivo con métricas y comparación de modelos
- [ ] Documentación: cómo usar, limitaciones, datos de entrenamiento

---

## Solución de Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| `OutOfMemory` durante entrenamiento | Batch size muy grande, modelo muy grande | Reducir `batch_size` de 128 a 32; usar `tf.keras.mixed_precision` para precisión mixta |
| Modelo overfitting rápidamente | Datos limitados, arquitectura muy compleja | Añadir dropout, usar L1/L2 regularization, data augmentation |
| Pérdida no disminuye (stuck) | Tasa de aprendizaje demasiado alta o muy baja | Usar `ReduceLROnPlateau` callback; probar lr entre 1e-5 y 1e-3 |
| `CUDA out of memory` | GPU insuficiente para modelo | Usar `tf.config.run_functions_eagerly(True)` para debug; compilar en CPU primero |
| Modelo no converge con BERT | Fine-tuning rate demasiado alto | Reducir learning rate a 2e-5; usar discriminative learning rates (capas iniciales más lentas) |
| Predicciones inconsistentes | Falta de reproducibilidad en datos | Fijar semillas: `tf.random.set_seed(42)`, `np.random.seed(42)`, `random.seed(42)` |
| Modelo muy lento en inferencia | Modelo muy grande, sin optimización | Usar DistilBERT; aplicar quantization; desplegar en ONNX o TFLite |
| Encoding issues en texto | Caracteres especiales corruptos | Asegurar UTF-8 en archivos CSV; usar `langdetect` para idioma |

---

## Herramientas y Librerías Clave

| Librería | Función | Instalación |
|----------|---------|-------------|
| `tensorflow` / `keras` | DL framework principal | `pip install tensorflow` |
| `transformers` | Modelos preentrenados (Hugging Face) | `pip install transformers` |
| `torch` | PyTorch (alternativa/complemento) | `pip install torch` |
| `scikit-learn` | ML clásico + métricas | `pip install scikit-learn` |
| `numpy` | Operaciones numéricas | `pip install numpy` |
| `pandas` | Manipulación de datos | `pip install pandas` |
| `matplotlib` / `seaborn` | Visualización | `pip install matplotlib seaborn` |
| `langdetect` | Detección automática de idioma | `pip install langdetect` |

---

## Ejemplos de Uso

### Ejemplo 1: Clasificador de Sugerencias (LSTM Custom)

**Prompt para el agente:**
> "Construye un modelo LSTM desde cero para clasificar comentarios de TripAdvisor en: sugerencia, crítica, opinión. Incluye fine-tuning de hiperparámetros y reporte de evaluación."

**Acciones esperadas:**
1. Cargar y explorar dataset
2. Implementar modelo LSTM con dropout y regularización
3. Entrenar con early stopping
4. Evaluar con precision, recall, F1, confusion matrix
5. Generar gráficos de resultados

### Ejemplo 2: Adaptación de BERT Preentrenado

**Prompt:**
> "Fine-tunea DistilBERT para detectar si un comentario es una sugerencia o no. Añade capas custom y optimiza hiperparámetros."

**Acciones esperadas:**
1. Descargar DistilBERT desde Hugging Face
2. Tokenizar dataset con AutoTokenizer
3. Construir modelo con capas custom (Dropout, Dense)
4. Fine-tunear con learning rate bajo (2e-5)
5. Evaluar y comparar contra baseline

### Ejemplo 3: Comparación de Modelos

**Prompt:**
> "Entrena 3 modelos (Logistic Regression, LSTM, BERT) y compara en precisión, tiempo de entrenamiento y velocidad de inferencia. Recomienda el mejor."

**Acciones esperadas:**
1. Implementar 3 arquitecturas
2. Entrenar con mismo dataset y métricas
3. Crear tabla comparativa
4. Recomendar modelo según caso de uso (accuracy vs speed)

---

## Scripts Reutilizables

### Script 1: Entrenamiento End-to-End

```python
# full_training_pipeline.py
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def train_model(csv_path, model_type='lstm'):
    # Cargar datos
    df = pd.read_csv(csv_path)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        df['comment'], df['label'], test_size=0.2, random_state=42
    )
    
    # Preprocesar
    tokenizer = Tokenizer(num_words=5000)
    tokenizer.fit_on_texts(X_train)
    X_train_seq = pad_sequences(tokenizer.texts_to_sequences(X_train), maxlen=128)
    X_test_seq = pad_sequences(tokenizer.texts_to_sequences(X_test), maxlen=128)
    
    # Encoding labels
    le = LabelEncoder()
    y_train_enc = to_categorical(le.fit_transform(y_train))
    y_test_enc = to_categorical(le.transform(y_test))
    
    # Construir modelo
    if model_type == 'lstm':
        model = build_lstm_model(num_classes=len(le.classes_))
    elif model_type == 'dense':
        model = build_dense_model(num_classes=len(le.classes_))
    
    # Entrenar
    history = model.fit(
        X_train_seq, y_train_enc,
        epochs=10, batch_size=32,
        validation_split=0.2,
        callbacks=[EarlyStopping(monitor='val_loss', patience=3)]
    )
    
    # Evaluar
    y_pred = np.argmax(model.predict(X_test_seq), axis=1)
    print(classification_report(le.inverse_transform(np.argmax(y_test_enc, axis=1)), 
                                le.inverse_transform(y_pred)))
    
    # Guardar
    model.save(f'models/model_{model_type}.h5')
    return model, history

if __name__ == '__main__':
    model, hist = train_model('data_analysis/data/consolidated.csv', model_type='lstm')
```

---

## Referencias y Contexto del Proyecto

- **Dataset**: `data_analysis/data/Chile_all1_part*.csv` (comentarios TripAdvisor multiidioma)
- **Objetivo**: Clasificación de sugerencias vs críticas vs opiniones
- **Contexto**: Proyecto de Tesis de Ingeniería Civil Informática, PUCV
- **Modelos base**: BERT-base, DistilBERT, ALBERT, RoBERTa

---

## Versión y Mantenimiento

- **Versión**: 0.1 → Basada en TensorFlow 2.10+, Transformers, PyTorch
- **Última actualización**: 18 de Marzo de 2026
- **Autores del proyecto**: Fabrizzio Andrés Mura Lavarello, Matías Hernán Bugueño Bugueño

**Mejoras futuras:**
- Integración con Ray Tune para hyperparameter optimization
- AutoML con Auto-sklearn o TPOT
- Ensemble de modelos para reducir variance
- Explicabilidad: LIME, SHAP para interpretación de predicciones
- Despliegue con TensorFlow Serving o FastAPI