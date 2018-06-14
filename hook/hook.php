<?php

namespace sammo\img_service;

include(__DIR__.'/gogs_key.php');


setlocale(LC_ALL, 'ko_KR.UTF-8');

$raw_payload = $_POST['payload']??'false';
$valid_hmac = $_SERVER['HTTP_X_GOGS_SIGNATURE']??'';
$req_hmac = hash_hmac('sha256', $raw_payload, Key::KEY);

if($valid_hmac != $req_hmac){
    die('');
}

exec("git pull -q 2>&1", $output);

exec("git ls-files -z ../icons", $raw_img_list);
$raw_img_list = explode("\x00", $raw_img_list[0]);
$img_list = [];

foreach ($raw_img_list as $path) {
    $pos = strpos($path, '../icons/');
    if($pos === false){
        continue;
    }
    $path = substr($path, $pos + 9);


    $pathinfo = pathinfo($path);
    $dpath = $pathinfo['dirname'];
    $basename = $pathinfo['basename'];
    $filename = $pathinfo['filename'];

    if(!\key_exists($dpath, $img_list)){
        $img_list[$dpath] = [];
    }
    $img_list[$dpath][$filename] = $basename;

}

file_put_contents('list.json', json_encode($img_list));
