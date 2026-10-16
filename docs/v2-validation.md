# Validação — CodeDragon V2 revisão 2

Data: 16/10/2026. Todas as evidências desta revisão referem-se ao PNG final de **2.168.293 bytes**, SHA-256:

`e5420e75ae9ca6c9a1d54f13b771d5e1b4a3d5a13d5331a4ddd31987ad62a7b5`

## Alterações e origem

Esta é uma revisão posterior à V2 já instalada e ativa, conforme informado pelo usuário. A V2 anterior está no commit `6b3add420b52e307a664ca30985257791ebcc4f1`, SHA-256 `3648d95700b376609ffd0b63225d6dc255a2986b5c97b2b11be044a303f5f490`; aparece somente nas comparações. Relatórios antigos foram substituídos por resultados dos novos bytes.

A referência histórica permaneceu intacta. Uma nova referência canônica sem chifres orientou as tiras de ImageGen. Todos os **73 quadros foram alterados**, inclusive os 16 olhares. O crânio arredondado não contém chifres nem crista no topo; escamas pretas, olhos azuis, pequenas orelhas laterais, asas, cauda, moletom/capuz e emblema angular permanecem reconhecíveis.

Os seis quadros de `running` mostram trabalho sentado em banquinho, monitor e teclado sobre mesa compacta, em três quartos. As patas alternam o gesto de digitação, com pequenos ajustes de cabeça, olhos, asas, cauda e iluminação azul. O computador permite ver o rosto e o emblema. As duas corridas têm oito fases próprias, sem espelhar o logo, com azul mais perceptível nas patas, asas e cauda e prolongamentos curtos ligados ao sprite.

As fontes, prompts e seus hashes estão em `assets/source/v2-r2/`. O build verifica essas fontes, executa os scripts de extração/composição/registro/limpeza da skill Pets 0.1.6 e gera o PNG e as prévias. O ajuste determinístico de escala/apoio não redesenha anatomia nem equipamentos. [Método e reprodução](v2-r2-authoring.md).

## Testes reexecutados

| Verificação | Resultado | Evidência |
| --- | --- | --- |
| Preflight oficial `Pets.validate_pet_spritesheet` | `valid: true`, v2, sem erros, 2.168.293 bytes | [Pets](../assets/qa/pets-validation.json) |
| `validate_atlas.py --require-v2 --chroma-key #FF00FF` | `ok: true`, sem erros/avisos; PNG RGBA 1536 × 2288; RGB invisível zerado | [Estrutura](../assets/qa/atlas-validation.json) |
| `inspect_frames.py --require-components` nos quadros do PNG final | `ok: true`, sem erros/avisos; extração original por componentes, sem fatiamento presumido | [Quadros](../assets/qa/frame-inspection.json) |
| Validador local | `ok: true`; 73 ocupadas, 15 vazias; margens, manifesto, hashes dos quadros e todos os GIFs correspondentes | [Local](../assets/qa/local-validation.json) |
| Limpeza de bordas | Uma passagem, alpha preservado; relatório vinculado ao PNG codificado | [Chroma](../assets/qa/chroma-verification.json) |
| Continuidade dos 16 olhares | `ok: true`, sem buracos de alpha; três avisos quantitativos revisados | [Continuidade](../assets/qa/direction-continuity.json) |
| Revisão rotulada dos 16 olhares | Cardinais aprovados; cinco intermediários aceitos com aviso explícito | [Semântica](../assets/qa/direction-semantics.json) |
| Revisão cega por três revisores isolados | Quatro cardinais reconhecidos por unanimidade no eixo solicitado; maioria estrita por eixo | [Revisão cega](../assets/qa/blind-direction-review.json) |
| `validate_pet_quality.py` | `ok: true`, sem erros, com avisos revisados; desvio máximo de centro 1,5 px; razão máxima de largura 1,173 | [Quality gate](../assets/qa/quality-gate.json) |
| `python tools/test_validation.py` | **15 testes aprovados**, código de saída 0 | [Regressões](../assets/qa/regression-tests.json) |
| Segunda reconstrução independente | PNG **idêntico byte a byte**, mesmo SHA-256 | [Reprodução](../assets/qa/reproducibility.json) |
| Inspeção visual independente do contato final | Sem defeito visual bloqueante observado nos 73 quadros | [Revisão visual](../assets/qa/visual-review.json) |

Os quinze testes cobrem aprovação da entrega e rejeição de dimensões erradas, ausência de alpha, quadro vazio, ocupação de célula indevida, alteração de olhar, retorno de um olhar antigo com chifres, retorno do trabalho antigo sem computador, troca de direção da corrida, relatório de sucesso com hash antigo, fonte adulterada, ordem incorreta no manifesto, corte na margem, RGB invisível e fundo opaco. As corrupções ocorrem em arquivos temporários.

As assinaturas dos quadros fixam os pixels revisados; não são detectores semânticos de chifres ou de computadores. Os GIFs decodificados são comparados aos compostos do PNG final, com tolerância de paleta. A validação oficial comprova aceitação estrutural e não substitui inspeção visual ou testes do reprodutor nativo.

## Movimento, transparência e olhares

Foram revisados o contato dos 73 quadros, as poses ordenadas, prévias por estado, comparações com a V2 anterior, os 16 olhares rotulados e randomizados e amostras sobre fundos claro/escuro. Os PNGs/GIFs e o MP4 sem áudio foram regenerados a partir do PNG codificado final. As sequências permitem conferir alternância de patas, pequena variação do monitor e energia azul acompanhando as poses de locomoção. Não há clipping de computador, cadeira, corpo, asas ou cauda nas células finais.

O salto mantém as bases `[200, 171, 145, 169, 200]` com alpha > 0 e elevação de 55 px. O quality gate usa alpha > 16 e mede `[198, 169, 143, 167, 198]`, também 55 px, com pouso a 1 px do idle por esse limiar. A diferença vem da borda semitransparente.

A ordem de olhar permanece 0° acima, sentido horário em passos de 22,5°, 90° direita, 180° abaixo e 270° esquerda. Os quatro cardinais foram reconhecidos pelos três revisores. As direções 67,5°, 112,5°, 202,5°, 247,5° e 292,5° são sutis. Em 112,5°, dois revisores cegos viram o eixo vertical como ambíguo; na revisão rotulada a cabeça baixa levemente em relação a 90°, preservando o quadrante pretendido. Em 202,5°, um revisor viu apenas abaixo; dois reconheceram abaixo/esquerda. Esses casos são avisos, não prova de ângulos físicos exatos.

As transições `157,5 → 180` e `337,5 → 0` têm diferenças de pixels maiores que as vizinhas. A primeira tem razão de área visível **1,24×**. Foram mantidas como avisos após a revisão em tamanho nativo: não se observou inversão, quadrante errado, buraco de alpha, deslocamento de centro ou alteração bloqueante de identidade/registro. A razão máxima de largura é 1,173 e o deslocamento de centro em relação ao idle não excede 1,5 px. As métricas estão preservadas integralmente, sem reduzir limiares para esconder falhas.

## Rastro e limites

A [documentação oficial de Pets](https://learn.chatgpt.com/docs/pets), consultada em 16/10/2026, e os esquemas das ferramentas disponíveis não expõem callbacks de arraste, partículas externas, controle de coordenadas ou efeitos persistentes. [Inventário e conclusão](../assets/qa/drag-capabilities.json).

**Rastro persistente ao arrastar não implementado por ausência de suporte exposto.** O efeito entregue é a energia azul incorporada aos quadros de locomoção. Ela se move com o pet e não fica no caminho nem desaparece por temporizador independente. Não foram alterados arquivos internos do aplicativo, nem criados overlays, injeções, áudio, som, voz ou TTS.

Nenhuma sessão de upload, criação, substituição, seleção ou importação foi executada. A V2 instalada permanece intacta. Reprodução desta revisão com eventos reais do host aguarda importação controlada e avaliação no aplicativo; a cadência demonstrativa dos GIFs não configura esse host. A documentação pública de upload web descreve v1; o plugin disponível validou o v2 desta revisão. A atualização deve usar um fluxo compatível com v2, preservando a entrada anterior. [Instruções](../README.md#atualizar-preservando-a-v2-instalada).

Não havia ferramenta Library exposta nesta sessão. Fontes, prompts, arte final, prévias e QA foram preservados no repositório, sem alegar publicação na Library.
