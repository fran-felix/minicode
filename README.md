# minicode
Another AI agent university project. Simple code agent.

Some code was made based on colab classes used during the course, or taken from them and adjusted.

## AUTORIA
Francisco Félix de Barros

Link do vídeo de apresentação (entrega 1):

## PASSO A PASSO PARA IMPLANTAÇÃO
- Clone o repositório do github (main branch):
  git clone https://github.com/fran-felix/minicode.git

- Configure um arquivo de variáveis ambiente (.env):
  - MINICODE_KEY, a chave de API do modelo (no caso do trabalho, fornecida pelo Laboratório de Inteligência Artificial - LIA)
  - MINICODE_MODEL, o nome do modelo
  - MINICODE_URL, a url para onde o modelo está hospedado

- Executando o projeto:
  - Na raiz do projeto: uv sync
  - source .venv/bin/activate
  - uv run python -m minicode.main

## ARQUITETURA
### Classes:
- MyAgent: classe que encapsula os tratamentos da API da OpenAI, controla o fluxo principal do agente e estabelece os prompts e a retroalimentação do modelo ao longo da execução.
- Validator: classe responsável por controlar a máquina de estados finitos que organiza os estágios de execução do agente, barrando a possibilidade de certas decisões em momentos inoportunos.

### Outros elementos estruturais:
Além de classes propriamente ditas, existem outros elementos do código vitais para o seu funcionamento:
- registry.py: contém todo o código de formatação do agente, organizando em esquemas e métodos extratores a informação que entra e sai do agente. Determina como o agente deve falar e operar.
- tools.py: codifica as ferramentas disponíveis ao agente, com sua implementação e o dicionário que descreve as ferramentas. Além disso, também implementa os métodos que monitoram o funcionamento do tool calling do agente ao longo da execução.

### Ferramentas implementadas:
- list_files: lista dos nomes dos arquivos no diretório de desenvolvimento
- read_file: permite o agente ler conteúdo de um arquivo no diretório de desenvolvimento, apenas leitura
- write_file: insere texto em um arquivo existente do diretório de desenvolvimento
- create_file: cria um arquivo novo no diretório de desenvolvimento
- ask_for_information: permite o modelo pedir informação adicional ao usuário em tempo de execução
- run_command: executa um comando de verificação no diretório de desenvolvimento
- nenhuma: informa que nenhuma ferramenta disponível pode executar a ação necessária, a válvula de escape do modelo
- answer: resposta final do agente

## FERRAMENTAS UTILIZADAS
- OpenAI API para instanciação e comunicação com a LLM
- VSCode WSL como ambiente de desenvolvimento
- UV para lidar com dependências do projeto e configurar o ambiente
- Ambiente virtual Python

## FERRAMENTAS DE IA UTILIZADAS
- GitHub Copilot para auxílio na implementação e geração de código quando necessário
- ChatGPT para compreensão inicial de pontos mais desafiadores das especificações do trabalho