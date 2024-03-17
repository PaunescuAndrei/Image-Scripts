$python = "python"
$script = "D:\Wallpapers\scripts\imgmagick_resize.py"
$customArgs = "-gtmp", "-nojpg", "-resize", "2500", "-cjpg", "95" 
$argumentsString = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
$arguments = $customArgs + $argumentsString

Start-Process -NoNewWindow -FilePath $python -ArgumentList @($script +" "+ $arguments)






