#为测试而生的初始化数据库命令

#如果有awesome数据库，就删除掉
drop database if exists awesome;
#重新建立一个awesome数据库
create database awesome;
#把awesome切换为当前用数据库
use awesome;
#给'www-data'@'127.0.0.1'用户设置awesome数据库下所有表以select，insert，update，delete 的权限
grant select, insert, update, delete on awesome.* to 'www-data'@'127.0.0.1' identified by 'www-data';
#创建表users
create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;
#
create table vendor (
    `vendor_id` int not null auto_increment,
    `vendor_name` varchar(50) not null,
    primary key (`vendor_id`)
) engine=innodb default charset=utf8;
#
create table model (
    `model_id` int not null auto_increment,
    `vendor_id` int not null,
    `model_name` varchar(50) not null,
    primary key (`model_id`),
    INDEX `vendor_id_idx` (`vendor_id` ASC),
    CONSTRAINT `vendor_id`
        FOREIGN KEY (`vendor_id`)
        REFERENCES `awesome`.`vendor` (`vendor_id`)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
) engine=innodb default charset=utf8;
#
create table firmware (
    `firmware_id` int not null auto_increment,
    `user_id` varchar(50) not null,
    `user_email` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `fw_vendor_name` varchar(50) not null,
    `fw_model_name` varchar(50) not null,
    `fw_type` varchar(50) not null,
    `fw_drive_format` varchar(50) not null,
    `fw_drive_linkspeed` varchar(50) not null,
    `firmware_revision` varchar(50) not null,
    `firmware_name` varchar(100) not null,
    `changelist_name` varchar(100) not null,
    `changelist_status` varchar(50) not null,
    `fw_release_date` varchar(50) not null,
    `created_at` real not null,
    #key `idx_created_at` (`created_at`),
    primary key (`firmware_id`),
    -- INDEX `fw_model_id_idx` (`fw_model_id` ASC),
    -- INDEX `fw_vendor_id_idx` (`fw_vendor_id` ASC),
    INDEX `idx_created_at` (`created_at` ASC)
    -- CONSTRAINT `fw_model_id`
    --     FOREIGN KEY (`fw_model_id`)
    --     REFERENCES `awesome`.`model` (`model_id`)
    --     ON DELETE NO ACTION
    --     ON UPDATE NO ACTION,
    -- CONSTRAINT `fw_vendor_id`
    --     FOREIGN KEY (`fw_vendor_id`)
    --     REFERENCES `awesome`.`vendor` (`vendor_id`)
    --     ON DELETE NO ACTION
    --     ON UPDATE NO ACTION
) engine=innodb default charset=utf8;
#