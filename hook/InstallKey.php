<?php
namespace sammo\img_service;

header('Content-Type: application/json');


$json_response = [
    'result'=>false,
    'reason'=>'Unknown',
];

$key = $_REQUEST['key']??'';

if (!$key) {
    $json_response['reason'] = 'no key';
    die(json_encode($json_response));
}

if (strlen($key)<16) {
    $json_response['reason'] = 'key is too short';
    die(json_encode($json_response));
}

$keyExists = file_exists(__DIR__.'/HashKey.php');
if($keyExists){
    $json_response['reason'] = 'already exists';
    die(json_encode($json_response));
}

$keyTemplate = file_get_contents(__DIR__.'/HashKey.orig.php');
$keyFile = str_replace('=HashKey=', $key, $keyTemplate);
file_put_contents(__DIR__.'/HashKey.php', $keyFile);

$json_response['result'] = true;
$json_response['reason'] = 'success';
die(json_encode($json_response));