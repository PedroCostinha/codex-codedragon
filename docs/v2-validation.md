# Evidências de validação — CodeDragon V2

Data: 16/10/2026. Os resultados se referem ao PNG com SHA-256:

`3648d95700b376609ffd0b63225d6dc255a2986b5c97b2b11be044a303f5f490`

## Origem e alterações

A V1 veio do commit `cd9aad5fcdf4eb91bc3a003e26fd2d23f5c6dd37`, na `main`, sem alterações locais ou commits exclusivos pendentes. As referências remotas foram atualizadas antes da criação de `feat/codedragon-v2-animations`.

O original é PNG RGBA, 1536 × 2288, grade 8 × 11, 73 quadros obrigatórios e 15 células vazias. Passou no preflight oficial antes da edição. Seu SHA-256 é `f81bdbb0d2701f21602a1b4cf5950026e46895235f680aa401d58d48e49753bd`.

Foi usada edição programática autorizada na missão, com controles locais de respiração, cabeça, asas, cauda, mãos e pés. O desenho é amostrado uma vez por pose em alpha pré-multiplicado. A região do emblema é protegida e nenhuma direção é espelhada. Os 57 quadros de animação apresentam alterações além do simples alinhamento vertical; os 16 olhares são pixel-idênticos. A imagem de referência e o manifesto não foram alterados.

## Testes executados

| Verificação | Resultado | Evidência |
| --- | --- | --- |
| Preflight oficial Pets do PNG final | `valid: true`, v2, sem erros | [pets-validation.json](../assets/qa/pets-validation.json) |
| Validador da skill `validate_atlas.py --require-v2` | `ok: true`, sem erros ou avisos | [atlas-validation.json](../assets/qa/atlas-validation.json) |
| Alpha, margens, células, manifesto, preservação dos olhares e fidelidade dos GIFs | `ok: true`; 73/15 células; 57 quadros modificados | [local-validation.json](../assets/qa/local-validation.json) |
| Inspeção de todos os quadros com `inspect_frames.py` | `ok: true`, sem erros ou avisos | [frame-inspection.json](../assets/qa/frame-inspection.json) |
| Chroma e bordas pelo validador da skill | Zero pixels de chroma, franjas verdes ou RGB escondido sob alpha zero | [chroma-verification.json](../assets/qa/chroma-verification.json) |
| Continuidade dos olhares com `measure_direction_continuity.py` | `ok: true`; dois avisos; sem buracos internos de alpha | [direction-continuity.json](../assets/qa/direction-continuity.json) |
| Verificação final com `validate_pet_quality.py` | `ok: true`, com avisos revisados dos olhares | [quality-gate.json](../assets/qa/quality-gate.json) |
| Testes de regressão | 9 aprovados | `python tools/test_validation.py` |

Os nove testes cobrem: aprovação da entrega, rejeição de dimensões erradas, ausência de alpha, pose vazia, ocupação de célula sem uso, alteração de olhar, corte na borda, RGB escondido e fundo opaco. Os casos corrompidos são temporários e não alteram a spritesheet distribuída.

As ferramentas da skill utilizadas são externas ao repositório, do plugin Pets 0.1.6. O relatório de chroma agrega as contagens reais de `validate_atlas.py`; não houve geração em chroma nem necessidade de despill. O preflight oficial foi executado pela ferramenta disponível, sem preparar upload ou modificar a coleção de pets.

## Revisão visual e movimento

Foram inspecionados a spritesheet original, a referência, células ampliadas, o contato dos 73 quadros finais, a sequência de cinco quadros do salto, a prancha dos 16 olhares e amostras sobre fundos claro e escuro. As prévias animadas e comparações usam o PNG final, e a validação local compara cada quadro GIF decodificado ao quadro correspondente com tolerância para sua paleta reduzida.

- Idle: respiração, piscada já existente, movimentos locais de asas/cauda e diferença de loop inferior à maior transição interna medida; sem troca de personagem.
- Trabalho: mãos alternadas, olhar concentrado original, leve avanço da cabeça e acompanhamento das asas; não usa a corrida de locomoção.
- Revisão/espera: gestos pequenos e distintos, com as expressões e poses aprovadas preservadas.
- Corridas: arte original própria para cada direção, apoio estabilizado, membros alternados e oscilações de asas/cauda. Não houve inversão do emblema.
- Erro: cabeça e asas baixam, cauda cede e fumaça original recebe tom cinza-azulado, seguida de recuperação.
- Saudação: amplitude maior no aceno e movimento pequeno da cabeça.
- Sucesso: preparação, subida, auge a 55 px da base, celebração com chama ligada à boca, retorno ao chão. O original tinha 30 px de elevação.

Com alpha maior que zero, as bases do salto são `[200, 171, 145, 169, 200]`; com limiar alpha > 16, a ferramenta da skill mede `[197, 169, 143, 167, 198]`. Ambos os critérios medem elevação de 55 px e pouso alinhado ao idle. A diferença de coordenadas decorre dos pixels de borda semitransparentes. Não é alteração de geometria entre relatórios.

As oito direções intermediárias mais sutis estão explicitamente marcadas como avisos na [revisão rotulada](../assets/qa/direction-semantics.json). Os quatro cardinais permanecem reconhecíveis. As transições `270 → 292,5` e `337,5 → 0` geram avisos de diferença local, com pequeno deslocamento de centro e sem mudança de escala relevante. Como os olhares não foram editados, foram preservados e registrados como limitação herdada. Não foi realizada uma nova revisão cega independente nesta V2.

As métricas de diferença ajudam a detectar saltos, mas não demonstram por si só fluidez. A revisão visual desta entrega usa quadros ordenados e prévias derivados da arte; não equivale à observação de todas as animações no reprodutor nativo. A cadência dos GIFs é demonstrativa, controlada pelo gerador de prévias.

## Não executado e limitações

- Importação, substituição e seleção da V2 na conta: **não executadas**. O pet instalado foi preservado.
- Reprodução da V2 com eventos reais de tarefa, teste, revisão e commit: **pendente de importação e avaliação no aplicativo**.
- Voo livre, estados adicionais, callbacks e balões personalizados: nenhuma API suportada foi encontrada nas ferramentas e [documentação oficial consultada](https://learn.chatgpt.com/docs/pets). Não implementados.
- Mensagens do README: exemplos conceituais; nenhum texto está ligado a eventos reais.
- MP4: não gerado; as demonstrações são GIF/PNG. Não há áudio.
- Library: não havia ferramenta de Library exposta nesta sessão; as evidências foram salvas no repositório, sem alegar publicação na Library.

A documentação pública descreve upload web v1, enquanto o plugin desta sessão valida v2. A aceitação no plugin está confirmada; a disponibilidade de importação em outras interfaces não está. O manifesto mantém apenas sua função descritiva e não configura ações nativas.

## Reprodução local

Com Python, Pillow 12.3.0, NumPy 2.3.5 e o histórico original do repositório:

```sh
python tools/build_v2.py
python tools/validate_v2.py
python tools/test_validation.py
```

O build verifica o hash da fonte, não altera a referência e não acumula transformações na V2. Uma mudança no PNG invalida os relatórios oficiais anteriores; execute novamente `validate_pet_spritesheet` com o caminho absoluto do novo PNG. Não publique um relatório antigo como evidência de novos bytes.
