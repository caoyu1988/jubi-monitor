DROP TABLE IF EXISTS jb_coin;
CREATE TABLE jb_coin(
  id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `code` VARCHAR(16) NOT NULL,
  `name` VARCHAR(32) NOT NULL
) COMMENT='币信息表';

DROP TABLE IF EXISTS jb_coin_ticker;
CREATE TABLE `jb_coin_ticker` (
  `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `pk` INT(11) NOT NULL,
  `coin` VARCHAR(16) NOT NULL,
  `price` DECIMAL(18,6) NOT NULL DEFAULT 0,
  UNIQUE(`pk`, `coin`)
) COMMENT='行情表';

DROP TABLE IF EXISTS jb_coin_increase;
CREATE TABLE jb_coin_increase(
  id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  coin VARCHAR(16) NOT NULL,
  pk INT NOT NULL,
  rate DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '涨幅',
  UNIQUE(pk, coin)
) COMMENT = '币值涨幅';