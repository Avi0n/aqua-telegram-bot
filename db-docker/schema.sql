SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

CREATE DATABASE IF NOT EXISTS `room1` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `room1`;

CREATE TABLE IF NOT EXISTS `media_hash` (
  `message_id` int(11) NOT NULL,
  `hash` varchar(255) NOT NULL,
  `date` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `message_karma` (
  `message_id` int(11) NOT NULL,
  `username` varchar(20) DEFAULT NULL,
  `thumbsup` tinyint(4) NOT NULL,
  `ok_hand` tinyint(4) NOT NULL,
  `heart` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_chat_id` (
  `chat_id` int(11) DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_karma` (
  `username` varchar(255) NOT NULL,
  `karma` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


CREATE DATABASE IF NOT EXISTS `room2` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `room2`;

CREATE TABLE IF NOT EXISTS `media_hash` (
  `message_id` int(11) NOT NULL,
  `hash` varchar(255) NOT NULL,
  `date` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `message_karma` (
  `message_id` int(11) NOT NULL,
  `username` varchar(20) DEFAULT NULL,
  `thumbsup` tinyint(4) NOT NULL,
  `ok_hand` tinyint(4) NOT NULL,
  `heart` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_karma` (
  `username` varchar(255) NOT NULL,
  `karma` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


CREATE DATABASE IF NOT EXISTS `room3` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `room3`;

CREATE TABLE IF NOT EXISTS `media_hash` (
  `message_id` int(11) NOT NULL,
  `hash` varchar(255) NOT NULL,
  `date` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `message_karma` (
  `message_id` int(11) NOT NULL,
  `username` varchar(20) DEFAULT NULL,
  `thumbsup` tinyint(4) NOT NULL,
  `ok_hand` tinyint(4) NOT NULL,
  `heart` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_karma` (
  `username` varchar(255) NOT NULL,
  `karma` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
