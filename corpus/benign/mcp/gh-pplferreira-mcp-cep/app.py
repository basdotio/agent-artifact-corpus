from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("CEP")

@mcp.tool()
def consultar_cep(cep: str) -> dict | None:
    """
    Consulta informações de um CEP usando a API ViaCEP.

    Parâmetros:
    - cep (str): CEP no formato '01001000'

    Retorno:
    - dict com dados do CEP, ou None em caso de erro
    """
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        return resposta.json()
    except requests.exceptions.RequestException as erro:
        print(f"Erro na requisição: {erro}")
        return None

# Exemplo de uso
if __name__ == "__main__":
    cep_input = input("Digite o CEP (somente números): ")
    resultado = consultar_cep(cep_input)

    if resultado:
        print("Dados do CEP:")
        for chave, valor in resultado.items():
            print(f"{chave}: {valor}")
    else:
        print("Falha ao consultar o CEP.")
