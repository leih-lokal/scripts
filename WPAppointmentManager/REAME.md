# AppointmentManager



The appointmanager is a script that makes reservations for items in our system. It runs as a GitHub workflow either on fixed intervals or via a webhook. Additionally, it un-reserves items if they have not been collected on the reservation day.



The webhook can be invoked by a php script that is triggered once a reservation has been made. The PHP script needs to be somewhere inside the WordPress document and be called when the AppointmentHourBooking plugin makes a reservation. For simplicitiy, we simply add the code to WordPress using **[Insert PHP Code Snippet](https://wordpress.org/plugins/insert-php-code-snippet/)**.  Simply add the code below and enter the shortcode in a page that should trigger the workflow (e.g. confirmation page).



```php
<?php

$url = "https://api.github.com/repos/leih-lokal/scripts/dispatches";

$curl = curl_init($url);
curl_setopt($curl, CURLOPT_URL, $url);
curl_setopt($curl, CURLOPT_POST, true);
curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);

$headers = array(

   "Accept: application/vnd.github.everest-preview+json",
   "Authorization: token GITHUB_ACCESS_TOKEN",
   "User-Agent: WordPress PHP Raw",
   "Content-Type: application/json",
);
curl_setopt($curl, CURLOPT_HTTPHEADER, $headers);

$data = <<<DATA
{
	"event_type":"webhook"
} 
DATA;

curl_setopt($curl, CURLOPT_POSTFIELDS, $data);

$resp = curl_exec($curl);
curl_close($curl);
?>
```