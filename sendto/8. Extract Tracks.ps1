$python = "python"
$script = "D:\Programs\Scripts\extract_tracks.py"
$argumentsString = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
$arguments = $argumentsString

Start-Process -Wait -NoNewWindow -FilePath $python -ArgumentList @($script +" "+ $arguments)
echo "`nExtraction finished."





