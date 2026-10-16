# Fontes e reprodução da revisão 2

Esta revisão posterior à V2 já instalada foi editada com a ferramenta ImageGen integrada. A referência histórica em `assets/reference/codedragon.png` permanece intacta; seus chifres não fazem parte da nova arte distribuída.

## Fontes versionadas

`assets/source/v2-r2/` contém a referência canônica sem chifres, os prompts efetivamente usados, nove tiras de animação, quatro âncoras cardinais e duas tiras de oito olhares. `sources.json` registra os SHA-256 dessas fontes; `approved-frames.json` fixa os pixels das 73 células após a revisão visual. A assinatura de um quadro detecta alterações posteriores, mas não reconhece visualmente chifres, anatomia ou digitação.

O build não consulta ImageGen nem depende de uma geração aleatória. Para alterar a arte, edite a tira correspondente com a referência canônica, revise a família inteira de poses e renove os hashes apenas após inspecionar o resultado. Não edite somente o PNG final.

## Pipeline

Os quatro utilitários em `tools/pet_pipeline/` são cópias sem modificações dos scripts de extração, composição, registro de olhares e limpeza de bordas da skill Pets 0.1.6. Os hashes em `provenance.json` verificam essa origem. O build executa esses utilitários em sequência e falha se qualquer etapa retornar erro.

1. Verifica as fontes e os utilitários por SHA-256.
2. Extrai grupos de componentes conectados, sem fatiar tiras de espaçamento irregular em posições presumidas.
3. Aplica um único fator de escala a cada linha, mantendo as diferenças de tamanho entre suas poses; centraliza e registra o apoio. A arte em pé tem aproximadamente 132 px de altura, próxima à V2 anterior. A cena sentada com computador usa até 148 px. Não se desenham membros ou equipamentos por código.
4. Mantém as cinco bases do salto anterior: `200, 171, 145, 169, 200`, uma elevação de 55 px dentro da célula.
5. Compõe as nove linhas, registra a linha 9 e usa o mesmo fator de registro para a linha 10.
6. Faz uma passagem de limpeza de bordas, preservando alpha e zerando RGB invisível, e codifica o PNG final.
7. Relê o PNG codificado e produz contatos, GIFs, comparações com a V2 anterior e MP4 sem áudio.

As comparações leem o commit imutável `6b3add420b52e307a664ca30985257791ebcc4f1`. Esse PNG é apenas referência de comparação, nunca fonte para acumular transformações. Para um pacote sem histórico Git, forneça o PNG anterior com `--source`; seu hash é verificado. `--skip-previews` permite reconstruir somente o atlas sem esse histórico.

```sh
python -m pip install -r tools/requirements-dev.txt
python tools/build_v2.py
python tools/validate_v2.py
python tools/test_validation.py
```

Use as versões fixadas das dependências para reproduzir os bytes codificados. O diretório `tmp/` é ignorado. Os finais importáveis, fontes e evidências permanecem versionados.

## Validação adicional

Além dos validadores locais, esta revisão utiliza `inspect_frames.py`, `validate_atlas.py --require-v2`, `measure_direction_continuity.py` e `validate_pet_quality.py` da skill Pets 0.1.6, e o preflight oficial `Pets.validate_pet_spritesheet`. Os relatórios em `assets/qa/` estão vinculados ao hash do atlas final. Após qualquer mudança visual, reexecute as verificações e o preflight; um relatório antigo não prova novos bytes.

A sessão não expõe uma ferramenta Library. As fontes, prompts, prévias e evidências foram preservados no repositório, sem alegar publicação na Library.
