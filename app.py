from flask import Flask, request, jsonify, render_template
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
import io
import base64
from openai import OpenAI
from gtts import gTTS
from rapidfuzz import process
import os
from dotenv import load_dotenv
from flask_cors import CORS
import numpy as np
import easyocr

app = Flask(__name__)

CORS(app)

load_dotenv()

# medicamentos_validos = [
#     "Amoxicilina", "Dipirona", "Paracetamol", "Ibuprofeno", "Omeprazol",
#     "Prednisona", "Losartana", "Metformina", "Azitromicina", "Captopril",
#     "Cimegripe", "Buscopan", "Naramig", "Musculare", "Ritalina", "Busonid",
#     "Decongex", "Ibupril", "Paracetamol", "Dipirona", "Omeprazol", "ibuprofeno",
#     "prednisona", "losartana", "metformina", "azitromicina", "captopril",
# ]

reader = easyocr.Reader(['pt'], gpu=True)

@app.route('/')
def home():
    return render_template('index.html')  # Serve o arquivo HTML

@app.route('/upload', methods=['POST'])
def upload_file():
    # Recebe a imagem como base64
    data = request.get_json()
    image_data = data.get('image')


    if not image_data:
        return jsonify({"error": "No image data found"}), 400

    # Decodifica a imagem base64
    image_data = image_data.split(',')[1]  # Remove o prefixo "data:image/jpeg;base64,"
    img_data = base64.b64decode(image_data)
    img = Image.open(io.BytesIO(img_data))
    
    results = reader.readtext(np.array(img))
    img.save("teste.jpg")  # Salva a imagem para depuração

    #texto_extraido = pytesseract.image_to_string(img).strip()
    texto_extraido = " ".join([text for _, text, _ in results])

    if not texto_extraido:
        return jsonify({"error": "Nenhum texto foi detectado na imagem."}), 400
    
    #text_corrigido = corrigir_nomes_ocr(texto_extraido, medicamentos_validos)

    # Resume o texto com ChatGPT
    resumo = resumir_texto(texto_extraido)

    if not resumo or resumo.startswith("Erro"):
        return jsonify({"error": resumo}), 500

    try:
        tts = gTTS(resumo, lang='pt')
        audio_path = "static/audio/resumo.mp3"
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        tts.save(audio_path)
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar áudio: {e}"}), 500

    return jsonify({
        'extracted_text': texto_extraido,
        'summary': resumo,
        'audio_url': '/' + audio_path
    })

    #resumo = resumir_texto(text)

    # return jsonify({
    #         "extracted_text": text,
    #         "summary": resumo
    #     }), 200

# def corrigir_nomes_ocr(texto_ocr, lista_medicamentos, limite_score=85):
#     palavras = texto_ocr.split()
#     texto_corrigido = []

#     for palavra in palavras:
#         resultado = process.extractOne(palavra, lista_medicamentos, score_cutoff=limite_score)
#         if resultado:
#             melhor_match, score, _ = resultado
#             texto_corrigido.append(melhor_match)
#         else:
#             texto_corrigido.append(palavra)

#     return ' '.join(texto_corrigido)



def resumir_texto(texto):
    """ Envia o texto extraído para a API do ChatGPT para gerar um resumo. """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Erro: OPENAI_API_KEY não encontrada no ambiente."

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use este nome
            messages=[
                {"role": "system", "content": "Você é um assistente que resume textos de bulas de remédio."},
                {"role": "user", "content": f"Resuma o seguinte texto sobre o medicamento, colocando as principais informações sobre ele: {texto}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro ao gerar resumo: {e}"


# def testar_acuracia(testes, lista_medicamentos):
#     acertos = 0

#     for teste in testes:
#         img = Image.open(teste["imagem"])
#         texto_extraido = pytesseract.image_to_string(img).strip()

#         texto_corrigido = corrigir_nomes_ocr(texto_extraido, lista_medicamentos)

#         # Verifica se o nome esperado está no texto corrigido
#         if teste["esperado"].lower() in texto_corrigido.lower():
#             acertos += 1
#         else:
#             print(f"❌ Falha no teste para {teste['imagem']}.")
#             print(f"Esperado: {teste['esperado']} | Encontrado: {texto_corrigido}\n")

#     total = len(testes)
#     acuracia = (acertos / total) * 100
#     print(f"\n✅ Acurácia total: {acuracia:.2f}% em {total} testes.")

#     return acuracia


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
    # testes = [
    #     {"imagem": "./static/images/buscopan.jpg", "esperado": "Buscopan"},
    #     {"imagem": "./static/images/cimegripe_cartela.jpg", "esperado": "Cimegripe"},
    #     {"imagem": "./static/images/cimegripe.jpg", "esperado": "Cimegripe"},
    #     {"imagem": "./static/images/musculare.jpg", "esperado": "Musculare"},
    #     {"imagem": "./static/images/naramig.jpg", "esperado": "Naramig"},
    #     {"imagem": "./static/images/busonid.jpg", "esperado": "Busonid"},
    #     {"imagem": "./static/images/decongex.jpg", "esperado": "Decongex"},
    #     {"imagem": "./static/images/ibupril.jpg", "esperado": "Ibuprofeno"},
    #     {"imagem": "./static/images/musculare_cartela.jpg", "esperado": "Musculare"},
    #     {"imagem": "./static/images/omeprazol.jpg", "esperado": "Omeprazol"},
    # ]

    #testar_acuracia(testes, medicamentos_validos)

# @app.route('/transcribe', methods=['POST'])
# def transcribe_audio():
#     if 'audio' not in request.files:
#         return jsonify({"error": "Nenhum arquivo de áudio enviado"}), 400

#     audio_file = request.files['audio']

#     try:
#         client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#         transcription = client.audio.transcriptions.create(
#             model="whisper-1",
#             file=audio_file,
#             response_format="text",
#             language="pt"
#         )
#         return jsonify({"transcription": transcription})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


#     app.run(debug=True)

