-- ==================================================================
-- Central Inteligente de Seguros - banco de dados completo
-- ==================================================================
-- Arquivo GERADO AUTOMATICAMENTE por app/seed.py. Nao edite a mao:
-- suas alteracoes serao perdidas na proxima vez que o seed rodar.
--
-- Para recriar o banco a partir daqui:
--     sqlite3 database/central.db < sql/banco.sql
--
-- Ou, mais simples, rode:  python -m app.seed
--
-- TODOS OS DADOS SAO FICTICIOS.
-- ==================================================================

BEGIN TRANSACTION;
CREATE TABLE agreements (
	id INTEGER NOT NULL, 
	nome VARCHAR(60) NOT NULL, 
	descricao VARCHAR(200), 
	PRIMARY KEY (id), 
	UNIQUE (nome)
);
INSERT INTO "agreements" VALUES(1,'FENACON','Fed. Nac. das Empresas de Serviços Contábeis');
INSERT INTO "agreements" VALUES(2,'OPBB','Ordem dos Profissionais');
INSERT INTO "agreements" VALUES(3,'CORECON','Conselho Regional de Economia');
INSERT INTO "agreements" VALUES(4,'FenaSebrae','Federação Nacional Sebrae');
CREATE TABLE claims (
	id INTEGER NOT NULL, 
	protocolo VARCHAR(20) NOT NULL, 
	participante VARCHAR(120) NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	data_abertura DATE NOT NULL, 
	documentacao VARCHAR(60) NOT NULL, 
	documentacao_ok BOOLEAN NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (protocolo)
);
INSERT INTO "claims" VALUES(1,'SIN-0451','Antônio Ferreira','Morte','2026-07-30','Completa',1,'Em liberação');
INSERT INTO "claims" VALUES(2,'SIN-0448','Beneficiário — H. Costa','Morte','2026-07-26','Falta certidão',0,'Aguardando doc.');
INSERT INTO "claims" VALUES(3,'SIN-0455','Luís G. Pereira','Invalidez','2026-08-05','Falta laudo',0,'Em análise');
INSERT INTO "claims" VALUES(4,'SIN-0459','Maria E. Dias','Invalidez','2026-08-09','Completa',1,'Em análise');
CREATE TABLE commissions (
	id INTEGER NOT NULL, 
	competencia VARCHAR(7) NOT NULL, 
	papel VARCHAR(20) NOT NULL, 
	quem VARCHAR(80) NOT NULL, 
	premio_total FLOAT NOT NULL, 
	percentual FLOAT NOT NULL, 
	valor FLOAT NOT NULL, 
	descricao VARCHAR(120), 
	PRIMARY KEY (id)
);
INSERT INTO "commissions" VALUES(1,'03/2026','ESTIPULANTE','Sebrae Previdência',143100.0,10.0,14310.0,'10% do prêmio · repasse à Entidade');
INSERT INTO "commissions" VALUES(2,'03/2026','CORRETORA','Corretora parceira',143100.0,15.0,21465.0,'15% do prêmio · intermediação');
INSERT INTO "commissions" VALUES(3,'03/2026','SEGURADORA','ICATU',143100.0,75.0,107325.0,'75% do prêmio · risco e operação');
INSERT INTO "commissions" VALUES(4,'04/2026','ESTIPULANTE','Sebrae Previdência',157400.0,10.0,15740.0,'10% do prêmio · repasse à Entidade');
INSERT INTO "commissions" VALUES(5,'04/2026','CORRETORA','Corretora parceira',157400.0,15.0,23610.0,'15% do prêmio · intermediação');
INSERT INTO "commissions" VALUES(6,'04/2026','SEGURADORA','ICATU',157400.0,75.0,118050.0,'75% do prêmio · risco e operação');
INSERT INTO "commissions" VALUES(7,'05/2026','ESTIPULANTE','Sebrae Previdência',171800.0,10.0,17180.0,'10% do prêmio · repasse à Entidade');
INSERT INTO "commissions" VALUES(8,'05/2026','CORRETORA','Corretora parceira',171800.0,15.0,25770.0,'15% do prêmio · intermediação');
INSERT INTO "commissions" VALUES(9,'05/2026','SEGURADORA','ICATU',171800.0,75.0,128850.0,'75% do prêmio · risco e operação');
INSERT INTO "commissions" VALUES(10,'06/2026','ESTIPULANTE','Sebrae Previdência',186100.0,10.0,18610.0,'10% do prêmio · repasse à Entidade');
INSERT INTO "commissions" VALUES(11,'06/2026','CORRETORA','Corretora parceira',186100.0,15.0,27915.0,'15% do prêmio · intermediação');
INSERT INTO "commissions" VALUES(12,'06/2026','SEGURADORA','ICATU',186100.0,75.0,139575.0,'75% do prêmio · risco e operação');
INSERT INTO "commissions" VALUES(13,'07/2026','ESTIPULANTE','Sebrae Previdência',214700.0,10.0,21470.0,'10% do prêmio · repasse à Entidade');
INSERT INTO "commissions" VALUES(14,'07/2026','CORRETORA','Corretora parceira',214700.0,15.0,32205.0,'15% do prêmio · intermediação');
INSERT INTO "commissions" VALUES(15,'07/2026','SEGURADORA','ICATU',214700.0,75.0,161025.0,'75% do prêmio · risco e operação');
CREATE TABLE delinquency (
	id INTEGER NOT NULL, 
	participante VARCHAR(120) NOT NULL, 
	numero_apolice VARCHAR(20) NOT NULL, 
	cobertura VARCHAR(30) NOT NULL, 
	valor FLOAT NOT NULL, 
	dias_atraso INTEGER NOT NULL, 
	cobranca_enviada BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "delinquency" VALUES(1,'Patrícia Gomes','AP-2087','Morte + Invalidez',112.0,112,0);
INSERT INTO "delinquency" VALUES(2,'Alexandre Pinto','AP-1902','Morte',178.0,98,0);
INSERT INTO "delinquency" VALUES(3,'Rita Fonseca','AP-2044','Invalidez',90.0,91,0);
INSERT INTO "delinquency" VALUES(4,'Gustavo Nery','AP-2110','Morte + Invalidez',145.0,62,0);
INSERT INTO "delinquency" VALUES(5,'Helena Braga','AP-1975','Morte',88.0,34,0);
INSERT INTO "delinquency" VALUES(6,'Diego Martins','AP-2120','Invalidez',60.0,9,0);
CREATE TABLE invoices (
	id INTEGER NOT NULL, 
	agreement_id INTEGER NOT NULL, 
	competencia VARCHAR(7) NOT NULL, 
	vidas INTEGER NOT NULL, 
	movimentacoes INTEGER NOT NULL, 
	valor FLOAT NOT NULL, 
	data_vencimento DATE, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agreement_id) REFERENCES agreements (id)
);
INSERT INTO "invoices" VALUES(1,1,'07/2026',1128,34,74320.0,NULL,'A emitir');
INSERT INTO "invoices" VALUES(2,2,'07/2026',642,18,41870.0,NULL,'A emitir');
INSERT INTO "invoices" VALUES(3,3,'07/2026',489,11,30510.0,NULL,'A emitir');
INSERT INTO "invoices" VALUES(4,4,'07/2026',1651,42,68000.0,NULL,'A emitir');
INSERT INTO "invoices" VALUES(5,4,'06/2026',1640,0,67200.0,'2026-08-07','Pago');
INSERT INTO "invoices" VALUES(6,1,'06/2026',1115,0,73100.0,'2026-08-07','Pago');
INSERT INTO "invoices" VALUES(7,2,'06/2026',638,0,41200.0,'2026-08-07','Em aberto');
INSERT INTO "invoices" VALUES(8,3,'06/2026',485,0,30100.0,'2026-08-07','Pago');
CREATE TABLE login_history (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	email_informado VARCHAR(120) NOT NULL, 
	perfil_informado VARCHAR(20) NOT NULL, 
	sucesso BOOLEAN NOT NULL, 
	motivo VARCHAR(200), 
	ip VARCHAR(45), 
	data_hora DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE payments (
	id INTEGER NOT NULL, 
	competencia VARCHAR(7) NOT NULL, 
	matricula VARCHAR(20) NOT NULL, 
	segurado VARCHAR(120) NOT NULL, 
	cpf VARCHAR(14), 
	capital_morte FLOAT NOT NULL, 
	capital_invalidez FLOAT NOT NULL, 
	premio FLOAT NOT NULL, 
	codigo_modulo VARCHAR(10), 
	codigo_sub VARCHAR(10), 
	status VARCHAR(20) NOT NULL, 
	criado_em DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "payments" VALUES(1,'07/2026','100001','Ana Beatriz Souza','384.517.920-41',150000.0,150000.0,60.7,'101','01','Pago','2026-08-18 17:15:13.469538');
INSERT INTO "payments" VALUES(2,'07/2026','100002','Carlos Henrique Lima','617.283.945-08',200000.0,200000.0,81.1,'101','01','Pago','2026-08-18 17:15:13.469541');
INSERT INTO "payments" VALUES(3,'07/2026','100003','Fernanda Alves Rocha','275.619.438-70',120000.0,120000.0,50.1,'101','02','Pago','2026-08-18 17:15:13.469541');
INSERT INTO "payments" VALUES(4,'07/2026','100004','Gustavo Pereira Martins','948.160.372-59',250000.0,250000.0,102.0,'101','02','A pagar','2026-08-18 17:15:13.469541');
INSERT INTO "payments" VALUES(5,'07/2026','100005','Juliana Cristina Moraes','503.847.126-91',180000.0,180000.0,69.6,'101','01','Pago','2026-08-18 17:15:13.469542');
INSERT INTO "payments" VALUES(6,'07/2026','100006','Marcelo Augusto Nunes','861.395.704-22',100000.0,100000.0,42.3,'101','03','Pago','2026-08-18 17:15:13.469542');
INSERT INTO "payments" VALUES(7,'07/2026','100007','Patricia Oliveira Costa','429.851.630-17',220000.0,220000.0,88.7,'101','01','Em atraso','2026-08-18 17:15:13.469542');
INSERT INTO "payments" VALUES(8,'07/2026','100008','Ricardo Mendes Ferreira','796.214.853-64',300000.0,300000.0,122.0,'101','02','Pago','2026-08-18 17:15:13.469543');
INSERT INTO "payments" VALUES(9,'07/2026','100009','Simone Aparecida Lopes','154.762.398-53',160000.0,160000.0,64.7,'101','03','A pagar','2026-08-18 17:15:13.469543');
INSERT INTO "payments" VALUES(10,'07/2026','100010','Thiago Rodrigues Barros','682.940.517-85',140000.0,140000.0,56.9,'101','01','Pago','2026-08-18 17:15:13.469543');
CREATE TABLE pendencies (
	id INTEGER NOT NULL, 
	prioridade VARCHAR(10) NOT NULL, 
	titulo VARCHAR(120) NOT NULL, 
	referente VARCHAR(120), 
	responsavel VARCHAR(60), 
	prazo DATE, 
	documento VARCHAR(60), 
	documento_ok BOOLEAN NOT NULL, 
	resolvida BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "pendencies" VALUES(1,'Alta','Renovação vencendo','AP-2041 · Marcos Ribeiro','Corretora','2026-08-29','Apólice',1,0);
INSERT INTO "pendencies" VALUES(2,'Alta','Certidão de óbito faltante','SIN-0448 · H. Costa','Beneficiário','2026-08-22','Certidão faltante',0,0);
INSERT INTO "pendencies" VALUES(3,'Média','Laudo médico pendente','SIN-0455 · L. Pereira','Seguradora','2026-08-27','Laudo faltante',0,0);
INSERT INTO "pendencies" VALUES(4,'Média','Confirmação de comissão','AP-1987 · F. Lima','Financeiro','2026-09-02','Extrato',1,0);
INSERT INTO "pendencies" VALUES(5,'Baixa','Atualização de cadastro','AP-2115 · J. Andrade','Estipulante','2026-09-08','Cadastro',1,0);
CREATE TABLE policies (
	id INTEGER NOT NULL, 
	numero_apolice VARCHAR(20) NOT NULL, 
	participante VARCHAR(120) NOT NULL, 
	cpf VARCHAR(14), 
	matricula VARCHAR(20), 
	data_nascimento DATE, 
	cobertura VARCHAR(30) NOT NULL, 
	capital_morte FLOAT NOT NULL, 
	capital_invalidez FLOAT NOT NULL, 
	capital_total FLOAT NOT NULL, 
	premio_mensal FLOAT NOT NULL, 
	data_inicio DATE NOT NULL, 
	data_vencimento DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	codigo_modulo VARCHAR(10), 
	codigo_sub VARCHAR(10), 
	competencia VARCHAR(7), 
	origem VARCHAR(20), 
	criado_em DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "policies" VALUES(1,'AP-2041','Marcos A. Ribeiro','158.813.998-69','200001',NULL,'Morte + Invalidez',250000.0,250000.0,250000.0,101.25,'2025-08-29','2026-08-29','A renovar','101','01','07/2026','prototipo','2026-08-18 17:15:13.443181');
INSERT INTO "policies" VALUES(2,'AP-1899','Sonia R. Batista','879.730.911-41','200002',NULL,'Invalidez',0.0,100000.0,100000.0,40.5,'2025-08-31','2026-08-31','A renovar','101','01','07/2026','prototipo','2026-08-18 17:15:13.443184');
INSERT INTO "policies" VALUES(3,'AP-1987','Fernanda C. Lima','707.536.455-68','200003',NULL,'Morte',180000.0,0.0,180000.0,72.9,'2025-09-04','2026-09-04','A renovar','101','01','07/2026','prototipo','2026-08-18 17:15:13.443185');
INSERT INTO "policies" VALUES(4,'AP-2115','Joao P. Andrade','151.884.472-94','200004',NULL,'Invalidez',0.0,120000.0,120000.0,48.6,'2024-09-12','2026-09-12','A renovar','101','01','07/2026','prototipo','2026-08-18 17:15:13.443185');
INSERT INTO "policies" VALUES(5,'AP-2033','Claudia M. Souza','055.761.698-71','200005',NULL,'Morte + Invalidez',300000.0,300000.0,300000.0,121.5,'2025-09-20','2026-09-20','Ativa','101','01','07/2026','prototipo','2026-08-18 17:15:13.443186');
INSERT INTO "policies" VALUES(6,'AP-1954','Roberto Nunes','689.768.469-78','200006',NULL,'Morte',200000.0,0.0,200000.0,81.0,'2026-03-09','2027-03-09','Ativa','101','01','07/2026','prototipo','2026-08-18 17:15:13.443186');
INSERT INTO "policies" VALUES(7,'AP-2087','Patricia Gomes','809.320.819-67','200007',NULL,'Morte + Invalidez',350000.0,350000.0,350000.0,141.75,'2026-04-23','2027-04-23','Ativa','101','01','07/2026','prototipo','2026-08-18 17:15:13.443186');
INSERT INTO "policies" VALUES(8,'AP-2160','Eduardo Tavares','273.177.848-64','200008',NULL,'Morte',150000.0,0.0,150000.0,60.75,'2026-07-16','2027-07-16','Ativa','101','01','07/2026','prototipo','2026-08-18 17:15:13.443187');
INSERT INTO "policies" VALUES(9,'AP-3001','Ana Beatriz Souza','384.517.920-41','100001','1986-03-15','Morte + Invalidez',150000.0,150000.0,150000.0,60.7,'2025-09-22','2026-09-22','Ativa','101','01','07/2026','planilha','2026-08-18 17:15:13.443187');
INSERT INTO "policies" VALUES(10,'AP-3002','Carlos Henrique Lima','617.283.945-08','100002','1981-11-22','Morte + Invalidez',200000.0,200000.0,200000.0,81.1,'2025-10-22','2026-10-22','Ativa','101','01','07/2026','planilha','2026-08-18 17:15:13.443188');
INSERT INTO "policies" VALUES(11,'AP-3003','Fernanda Alves Rocha','275.619.438-70','100003','1990-07-08','Morte + Invalidez',120000.0,120000.0,120000.0,50.1,'2025-11-21','2026-11-21','Ativa','101','02','07/2026','planilha','2026-08-18 17:15:13.443188');
INSERT INTO "policies" VALUES(12,'AP-3004','Gustavo Pereira Martins','948.160.372-59','100004','1978-01-30','Morte + Invalidez',250000.0,250000.0,250000.0,102.0,'2025-12-21','2026-12-21','Ativa','101','02','07/2026','planilha','2026-08-18 17:15:13.443188');
INSERT INTO "policies" VALUES(13,'AP-3005','Juliana Cristina Moraes','503.847.126-91','100005','1993-05-19','Morte + Invalidez',180000.0,180000.0,180000.0,69.6,'2026-01-20','2027-01-20','Ativa','101','01','07/2026','planilha','2026-08-18 17:15:13.443189');
INSERT INTO "policies" VALUES(14,'AP-3006','Marcelo Augusto Nunes','861.395.704-22','100006','1984-12-11','Morte + Invalidez',100000.0,100000.0,100000.0,42.3,'2026-02-19','2027-02-19','Ativa','101','03','07/2026','planilha','2026-08-18 17:15:13.443189');
INSERT INTO "policies" VALUES(15,'AP-3007','Patricia Oliveira Costa','429.851.630-17','100007','1988-09-03','Morte + Invalidez',220000.0,220000.0,220000.0,88.7,'2026-03-21','2027-03-21','Ativa','101','01','07/2026','planilha','2026-08-18 17:15:13.443189');
INSERT INTO "policies" VALUES(16,'AP-3008','Ricardo Mendes Ferreira','796.214.853-64','100008','1975-02-27','Morte + Invalidez',300000.0,300000.0,300000.0,122.0,'2026-04-20','2027-04-20','Ativa','101','02','07/2026','planilha','2026-08-18 17:15:13.443190');
INSERT INTO "policies" VALUES(17,'AP-3009','Simone Aparecida Lopes','154.762.398-53','100009','1992-10-10','Morte + Invalidez',160000.0,160000.0,160000.0,64.7,'2026-05-20','2027-05-20','Ativa','101','03','07/2026','planilha','2026-08-18 17:15:13.443190');
INSERT INTO "policies" VALUES(18,'AP-3010','Thiago Rodrigues Barros','682.940.517-85','100010','1980-06-05','Morte + Invalidez',140000.0,140000.0,140000.0,56.9,'2026-06-19','2027-06-19','Ativa','101','01','07/2026','planilha','2026-08-18 17:15:13.443190');
INSERT INTO "policies" VALUES(19,'AP-4001','Igor Machado','002.978.753-47','304001','1989-07-31','Invalidez',0.0,150000.0,150000.0,60.75,'2025-10-07','2026-10-07','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443191');
INSERT INTO "policies" VALUES(20,'AP-4002','Juliano Neves','457.178.472-67','304002','2000-02-21','Morte + Invalidez',400000.0,400000.0,400000.0,162.0,'2026-08-17','2027-08-17','Ativa','101','01','07/2026','gerado','2026-08-18 17:15:13.443191');
INSERT INTO "policies" VALUES(21,'AP-4003','Sabrina Pacheco','627.010.798-19','304003','1968-02-12','Invalidez',0.0,100000.0,100000.0,40.5,'2025-08-17','2026-08-17','Vencida','101','01','07/2026','gerado','2026-08-18 17:15:13.443192');
INSERT INTO "policies" VALUES(22,'AP-4004','Priscila Dias','452.059.972-83','304004','1977-02-18','Morte + Invalidez',80000.0,80000.0,80000.0,32.4,'2026-05-29','2027-05-29','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443192');
INSERT INTO "policies" VALUES(23,'AP-4005','Isabela Teixeira','622.948.662-83','304005','1997-11-10','Morte + Invalidez',300000.0,300000.0,300000.0,121.5,'2025-10-05','2026-10-05','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443192');
INSERT INTO "policies" VALUES(24,'AP-4006','Adriana Dias','500.875.475-17','304006','1986-01-30','Invalidez',0.0,100000.0,100000.0,40.5,'2025-06-05','2026-06-05','Cancelada','101','02','07/2026','gerado','2026-08-18 17:15:13.443193');
INSERT INTO "policies" VALUES(25,'AP-4007','Karina Esteves','957.931.860-32','304007','1982-03-13','Morte + Invalidez',300000.0,300000.0,300000.0,121.5,'2025-08-23','2026-08-23','A renovar','101','01','07/2026','gerado','2026-08-18 17:15:13.443193');
INSERT INTO "policies" VALUES(26,'AP-4008','Daniel Oliveira','028.382.226-46','304008','1969-10-03','Morte + Invalidez',150000.0,150000.0,150000.0,60.75,'2026-01-12','2027-01-12','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443193');
INSERT INTO "policies" VALUES(27,'AP-4009','Emerson Carvalho','247.764.725-87','304009','1986-03-19','Invalidez',0.0,180000.0,180000.0,72.9,'2025-08-13','2026-08-13','Vencida','101','02','07/2026','gerado','2026-08-18 17:15:13.443194');
INSERT INTO "policies" VALUES(28,'AP-4010','Heitor Queiroz','330.175.682-05','304010','1997-05-28','Morte + Invalidez',180000.0,180000.0,180000.0,72.9,'2026-07-01','2027-07-01','Ativa','101','01','07/2026','gerado','2026-08-18 17:15:13.443194');
INSERT INTO "policies" VALUES(29,'AP-4011','Alexandre Ramos','319.489.394-94','304011','1977-07-01','Morte + Invalidez',350000.0,350000.0,350000.0,141.75,'2026-06-19','2027-06-19','Cancelada','101','03','07/2026','gerado','2026-08-18 17:15:13.443195');
INSERT INTO "policies" VALUES(30,'AP-4012','Isabela Dias','105.218.549-14','304012','1993-12-18','Invalidez',0.0,100000.0,100000.0,40.5,'2025-12-19','2026-12-19','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443195');
INSERT INTO "policies" VALUES(31,'AP-4013','Karina Ismael','460.013.041-18','304013','1983-03-08','Invalidez',0.0,100000.0,100000.0,40.5,'2025-05-17','2026-05-17','Vencida','101','03','07/2026','gerado','2026-08-18 17:15:13.443195');
INSERT INTO "policies" VALUES(32,'AP-4014','Alexandre Klein','906.593.976-15','304014','1972-04-12','Invalidez',0.0,350000.0,350000.0,141.75,'2026-03-26','2027-03-26','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443196');
INSERT INTO "policies" VALUES(33,'AP-4015','Rafael Machado','604.541.465-90','304015','1968-08-29','Invalidez',0.0,200000.0,200000.0,81.0,'2025-06-08','2026-06-08','Vencida','101','03','07/2026','gerado','2026-08-18 17:15:13.443196');
INSERT INTO "policies" VALUES(34,'AP-4016','Yasmin Guimaraes','291.102.859-40','304016','1996-08-06','Morte + Invalidez',80000.0,80000.0,80000.0,32.4,'2026-05-14','2027-05-14','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443196');
INSERT INTO "policies" VALUES(35,'AP-4017','Isabela Lacerda','632.280.886-42','304017','1990-11-30','Invalidez',0.0,220000.0,220000.0,89.1,'2025-11-19','2026-11-19','Ativa','101','01','07/2026','gerado','2026-08-18 17:15:13.443197');
INSERT INTO "policies" VALUES(36,'AP-4018','Bruno Almeida','452.912.808-45','304018','1982-11-26','Invalidez',0.0,300000.0,300000.0,121.5,'2026-01-10','2027-01-10','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443197');
INSERT INTO "policies" VALUES(37,'AP-4019','Wagner Barbosa','703.826.538-45','304019','1990-10-03','Morte + Invalidez',80000.0,80000.0,80000.0,32.4,'2026-03-27','2027-03-27','Ativa','101','01','07/2026','gerado','2026-08-18 17:15:13.443197');
INSERT INTO "policies" VALUES(38,'AP-4020','Beatriz Lacerda','794.326.270-58','304020','1977-01-11','Invalidez',0.0,400000.0,400000.0,162.0,'2025-12-30','2026-12-30','Cancelada','101','03','07/2026','gerado','2026-08-18 17:15:13.443198');
INSERT INTO "policies" VALUES(39,'AP-4021','Emerson Barbosa','584.210.839-49','304021','1988-03-26','Morte + Invalidez',120000.0,120000.0,120000.0,48.6,'2025-06-22','2026-06-22','Vencida','101','01','07/2026','gerado','2026-08-18 17:15:13.443198');
INSERT INTO "policies" VALUES(40,'AP-4022','Debora Machado','281.126.584-40','304022','1972-10-03','Morte + Invalidez',300000.0,300000.0,300000.0,121.5,'2026-06-29','2027-06-29','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443198');
INSERT INTO "policies" VALUES(41,'AP-4023','Mariana Freitas','526.309.765-82','304023','1988-11-02','Invalidez',0.0,180000.0,180000.0,72.9,'2026-02-11','2027-02-11','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443199');
INSERT INTO "policies" VALUES(42,'AP-4024','Bruno Freitas','018.051.543-82','304024','1994-04-18','Invalidez',0.0,300000.0,300000.0,121.5,'2025-07-23','2026-07-23','Vencida','101','03','07/2026','gerado','2026-08-18 17:15:13.443199');
INSERT INTO "policies" VALUES(43,'AP-4025','Priscila Esteves','164.941.577-18','304025','1996-10-30','Morte',200000.0,0.0,200000.0,81.0,'2026-01-13','2027-01-13','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443199');
INSERT INTO "policies" VALUES(44,'AP-4026','Priscila Lacerda','111.744.325-68','304026','1986-03-02','Morte + Invalidez',250000.0,250000.0,250000.0,101.25,'2026-03-05','2027-03-05','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443200');
INSERT INTO "policies" VALUES(45,'AP-4027','Yasmin Klein','652.373.556-96','304027','1979-07-11','Morte + Invalidez',400000.0,400000.0,400000.0,162.0,'2026-07-22','2027-07-22','Cancelada','101','01','07/2026','gerado','2026-08-18 17:15:13.443200');
INSERT INTO "policies" VALUES(46,'AP-4028','Jonas Oliveira','264.515.474-28','304028','1968-08-17','Morte + Invalidez',350000.0,350000.0,350000.0,141.75,'2026-04-11','2027-04-11','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443200');
INSERT INTO "policies" VALUES(47,'AP-4029','Sabrina Henriques','144.976.608-56','304029','1966-12-31','Invalidez',0.0,120000.0,120000.0,48.6,'2026-02-21','2027-02-21','Ativa','101','02','07/2026','gerado','2026-08-18 17:15:13.443201');
INSERT INTO "policies" VALUES(48,'AP-4030','Giovana Pacheco','883.655.062-04','304030','1971-09-13','Morte + Invalidez',400000.0,400000.0,400000.0,162.0,'2026-07-14','2027-07-14','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443201');
INSERT INTO "policies" VALUES(49,'AP-4031','Rafael Esteves','677.500.314-50','304031','1974-03-17','Invalidez',0.0,350000.0,350000.0,141.75,'2026-04-04','2027-04-04','Ativa','101','01','07/2026','gerado','2026-08-18 17:15:13.443201');
INSERT INTO "policies" VALUES(50,'AP-4032','Helena Queiroz','183.801.253-73','304032','1985-01-28','Invalidez',0.0,350000.0,350000.0,141.75,'2026-03-28','2027-03-28','Ativa','101','03','07/2026','gerado','2026-08-18 17:15:13.443202');
CREATE TABLE proposals (
	id INTEGER NOT NULL, 
	numero VARCHAR(20) NOT NULL, 
	participante VARCHAR(120) NOT NULL, 
	cobertura VARCHAR(30), 
	capital FLOAT, 
	etapa VARCHAR(20) NOT NULL, 
	observacao VARCHAR(120), 
	recusada BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (numero)
);
INSERT INTO "proposals" VALUES(1,'PROP-3012','Ricardo Alves','Morte + Invalidez',220000.0,'recebida',NULL,0);
INSERT INTO "proposals" VALUES(2,'PROP-3015','Juliana Reis','Morte',150000.0,'recebida',NULL,0);
INSERT INTO "proposals" VALUES(3,'PROP-3018','Carlos Menezes','Invalidez',120000.0,'recebida',NULL,0);
INSERT INTO "proposals" VALUES(4,'PROP-3008','Amanda Prado','Invalidez',NULL,'analise','DPS em avaliação',0);
INSERT INTO "proposals" VALUES(5,'PROP-3010','Bruno Carvalho','Morte + Invalidez',NULL,'analise','Aguardando análise',0);
INSERT INTO "proposals" VALUES(6,'PROP-2998','Teresa Lopes','Morte',NULL,'aceita','Emitir apólice',0);
INSERT INTO "proposals" VALUES(7,'PROP-3001','Felipe Duarte','Morte + Invalidez',NULL,'aceita','Emitir apólice',0);
INSERT INTO "proposals" VALUES(8,'PROP-3005','Sandra Vieira',NULL,NULL,'pendente','Falta DPS assinada',0);
INSERT INTO "proposals" VALUES(9,'PROP-2995','Otávio Ramos',NULL,NULL,'pendente','Recusada — risco agravado',1);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	nome VARCHAR(120) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	senha_hash VARCHAR(200) NOT NULL, 
	perfil VARCHAR(20) NOT NULL, 
	ativo BOOLEAN NOT NULL, 
	criado_em DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "users" VALUES(1,'Estipulante','estipulante@sebraeprev.com.br','$2b$12$h4gSr3tFwtVyl0j5vDMY4uUs6VKInY6r4.93.DnpBVwR1r5p6X3aG','ESTIPULANTE',1,'2026-08-18 17:15:13.425005');
INSERT INTO "users" VALUES(2,'Corretora','corretora@sebraeprev.com.br','$2b$12$u/Zd2luHqi1llStADbQHy.V2sdET9scUV2n37ZliAMqHdl7sVMZ1C','CORRETORA',1,'2026-08-18 17:15:13.425009');
INSERT INTO "users" VALUES(3,'Seguradora','seguradora@sebraeprev.com.br','$2b$12$cR9C44n.yBDMRH7o6SDVPeI.ekAkEEmg6WTKZ2jZq.pNZ4D2hLoVu','SEGURADORA',1,'2026-08-18 17:15:13.425010');
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_policies_participante ON policies (participante);
CREATE INDEX ix_policies_status ON policies (status);
CREATE UNIQUE INDEX ix_policies_numero_apolice ON policies (numero_apolice);
CREATE INDEX ix_policies_data_vencimento ON policies (data_vencimento);
CREATE INDEX ix_payments_status ON payments (status);
CREATE INDEX ix_payments_competencia ON payments (competencia);
CREATE INDEX ix_commissions_competencia ON commissions (competencia);
CREATE INDEX ix_proposals_etapa ON proposals (etapa);
CREATE INDEX ix_claims_status ON claims (status);
CREATE INDEX ix_pendencies_prioridade ON pendencies (prioridade);
CREATE INDEX ix_invoices_status ON invoices (status);
CREATE INDEX ix_invoices_competencia ON invoices (competencia);
COMMIT;
