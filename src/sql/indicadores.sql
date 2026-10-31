-- 1. Total de funcionários ativos no quadro extraído.
SELECT COUNT(*) AS total_de_funcionarios_ativos
FROM modelo_estrela.fato_quadro_funcionario
WHERE funcionario_atual;

-- 2. Funcionários ativos por departamento.
SELECT
    departamento.nome_departamento,
    COUNT(*) AS quantidade_de_funcionarios
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_departamento AS departamento
    ON departamento.chave_departamento = quadro.chave_departamento
WHERE quadro.funcionario_atual
GROUP BY departamento.nome_departamento
ORDER BY quantidade_de_funcionarios DESC;

-- 3. Funcionários ativos por cargo.
SELECT
    funcionario.cargo,
    COUNT(*) AS quantidade_de_funcionarios
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_funcionario AS funcionario
    ON funcionario.chave_funcionario = quadro.chave_funcionario
WHERE quadro.funcionario_atual
GROUP BY funcionario.cargo
ORDER BY quantidade_de_funcionarios DESC;

-- 4. Distribuição de funcionários por gênero e percentual do total.
SELECT
    COALESCE(funcionario.genero, 'Não informado') AS genero,
    COUNT(*) AS quantidade_de_funcionarios,
    100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0)
        AS percentual_do_quadro
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_funcionario AS funcionario
    ON funcionario.chave_funcionario = quadro.chave_funcionario
WHERE quadro.funcionario_atual
GROUP BY funcionario.genero
ORDER BY quantidade_de_funcionarios DESC;

-- 5. Novas contratações por ano.
SELECT
    calendario.ano,
    COUNT(*) AS quantidade_de_contratacoes
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_data AS calendario
    ON calendario.chave_data = quadro.chave_data_contratacao
GROUP BY calendario.ano
ORDER BY calendario.ano;

-- 6. Tempo médio de empresa dos funcionários atualmente ativos, em anos.
SELECT
    AVG(
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, calendario.data))
        + EXTRACT(MONTH FROM AGE(CURRENT_DATE, calendario.data)) / 12.0
    ) AS tempo_medio_de_empresa_em_anos
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_data AS calendario
    ON calendario.chave_data = quadro.chave_data_contratacao
WHERE quadro.funcionario_atual;

-- 7. Taxa de remuneração mais recente por funcionário, por departamento e
-- frequência de pagamento. Os valores de frequências distintas não são somados.
WITH remuneracao_mais_recente AS (
    SELECT DISTINCT ON (codigo_funcionario_origem)
        codigo_funcionario_origem,
        taxa_remuneracao,
        frequencia_pagamento
    FROM modelo_estrela.fato_historico_remuneracao
    ORDER BY codigo_funcionario_origem, data_alteracao DESC
)
SELECT
    departamento.nome_departamento,
    remuneracao.frequencia_pagamento,
    AVG(remuneracao.taxa_remuneracao) AS taxa_media_de_remuneracao,
    COUNT(*) AS quantidade_de_funcionarios
FROM remuneracao_mais_recente AS remuneracao
JOIN modelo_estrela.fato_quadro_funcionario AS quadro
    ON quadro.codigo_funcionario_origem =
        remuneracao.codigo_funcionario_origem
JOIN modelo_estrela.dimensao_departamento AS departamento
    ON departamento.chave_departamento = quadro.chave_departamento
WHERE quadro.funcionario_atual
GROUP BY departamento.nome_departamento, remuneracao.frequencia_pagamento
ORDER BY departamento.nome_departamento, remuneracao.frequencia_pagamento;

-- 8. Variação da taxa entre alterações consecutivas com a mesma frequência.
-- Não se comparam taxas quando a frequência de pagamento muda.
WITH variacoes AS (
    SELECT
        codigo_funcionario_origem,
        frequencia_pagamento,
        data_alteracao,
        taxa_remuneracao,
        LAG(frequencia_pagamento) OVER (
            PARTITION BY codigo_funcionario_origem
            ORDER BY data_alteracao
        ) AS frequencia_anterior,
        LAG(taxa_remuneracao) OVER (
            PARTITION BY codigo_funcionario_origem
            ORDER BY data_alteracao
        ) AS taxa_anterior
    FROM modelo_estrela.fato_historico_remuneracao
)
SELECT
    frequencia_pagamento,
    COUNT(*) AS quantidade_de_alteracoes_comparaveis,
    AVG(taxa_remuneracao - taxa_anterior) AS variacao_media_da_taxa,
    100.0 * SUM(taxa_remuneracao - taxa_anterior)
        / NULLIF(SUM(taxa_anterior), 0) AS variacao_percentual_acumulada
FROM variacoes
WHERE frequencia_pagamento = frequencia_anterior
GROUP BY frequencia_pagamento
ORDER BY frequencia_pagamento;

-- 9. Médias das horas de férias e de afastamento registradas por departamento.
SELECT
    departamento.nome_departamento,
    AVG(quadro.horas_ferias) AS media_de_horas_de_ferias,
    AVG(quadro.horas_afastamento) AS media_de_horas_de_afastamento,
    COUNT(*) AS quantidade_de_funcionarios
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_departamento AS departamento
    ON departamento.chave_departamento = quadro.chave_departamento
WHERE quadro.funcionario_atual
GROUP BY departamento.nome_departamento
ORDER BY departamento.nome_departamento;

-- 10. Funcionários ativos por turno de trabalho.
SELECT
    turno.nome_turno,
    turno.horario_inicio,
    turno.horario_fim,
    COUNT(*) AS quantidade_de_funcionarios
FROM modelo_estrela.fato_quadro_funcionario AS quadro
JOIN modelo_estrela.dimensao_turno AS turno
    ON turno.chave_turno = quadro.chave_turno
WHERE quadro.funcionario_atual
GROUP BY turno.nome_turno, turno.horario_inicio, turno.horario_fim
ORDER BY quantidade_de_funcionarios DESC;
