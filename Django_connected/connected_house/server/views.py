from django.shortcuts import render
from django.template import RequestContext
from django.contrib.auth import logout, login, authenticate
from django.shortcuts import redirect
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.db.models import Avg, Max, Min

from .forms import SignInForm, SignUpForm, EditAccountForm, SensorForms, BridgeForms, NewChannelForm
from website.models import User, Sensor, Data, Version, Bridge, Channel
import hashlib, random


# Create your views here.
#show index page
def index(request):
    context = {"page":"index"}
    user_email = request.session.get('user', None)
    if user_email:
        try:
            user = User.objects.get(email=user_email)
        except Exception as e:
            request.session.flush()
            return redirect('/')
        if user:
            context.update({"user": user_email})

    return render(request,'templates/index.html', context)

#show login page
def login(request, user):
    request.session['user'] = user.email
    return redirect('/dashboard/')

#show logout page
def logout(request):
    request.session.flush()
    return redirect('/')

#if user's signed in returns user, else show singin page
def check_auth(request):
    user_email = request.session.get('user', None)
    context = {"user": user_email}
    if not user_email:
        return redirect('/signin')
    else:
        try:
            user = User.objects.get(email=user_email)
        except Exception as e:
            request.session.flush()
            return redirect('/signin')
        return user

#show signin page
def signin(request):
    context = {"page":"signin", "loginremember": request.session.get('loginremember')}
    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
            
        is_valid = form.is_valid()
        if is_valid:
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember = form.cleaned_data['remember']
            # Use Cookie
            try:
                user = User.objects.get(email=email)
            except Exception as e:
                context['login_form'] = form
                context.update({"error": True})
                return render(request,'templates/signin.html', context)
            if check_password(password, user.password):
                return login(request, user)
    else:
        form = SignInForm(request)
    context['login_form'] = form
    return render(request,'templates/signin.html', context)

#show signup page
def signup(request):
    context = {"page":"signup"}
    if request.method == 'POST':
        form = SignUpForm(request, data=request.POST)
            
        is_valid = form.is_valid()

        if is_valid:
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            password2 = form.cleaned_data['password2']
            timezone = form.cleaned_data['timezone']
            user = User(name=name, email=email, password=make_password(password, salt=name+'connect2', hasher='default'), timezone=timezone, prefered_channel="null")
            user.save()
            return login(request, user)
    else:
        form = SignUpForm()
    context['login_form'] = form
    return render(request,'templates/signup.html', context)

#show dashboard page
def dashboard(request):
    context = {"page":"dashboard"}
    context.update({"user": check_auth(request).email})
    return render(request,'templates/dashboard.html', context)

#show my account page if user, else show signin page
def myaccount(request):
    context = {"page":"myaccount"}    
    user = check_auth(request)
    context = {"user": user.email}

    if user:
        context.update({
        'email': user.email,
        'name': user.name,
        'timezone': user.timezone,
        'api': user.API_KEY
        })
        # We do not put user to avoid placing the password in the template
        # even if it is hashed
    else:
        return redirect('/signin')
    return render(request,'templates/myaccount.html', context)


def generateapi(request):
    # This page (the html one) should ask for the user password to be type if a new key is requested    
    user = check_auth(request)
    API_KEY=hashlib.md5( str(random.getrandbits(256)) ).hexdigest()
    user.API_KEY=API_KEY
    user.save()
    return redirect('/myaccount')

#deletes current user
def myaccount_delete(request):
    # This page (the html one) should ask for the user password
    user = check_auth(request)
    user.delete()
    return logout(request)

#shows edit_account page
def myaccount_edit(request):
    context = {"page":"account_edit"}
    user = check_auth(request)
    context.update({"user": user.email})
    data = {'name': user.name, 'timezone': user.timezone}
    if request.method == 'POST':
        form = EditAccountForm(request, data=request.POST)
            
        is_valid = form.is_valid()

        if is_valid:
            name = form.cleaned_data['name']
            password = form.cleaned_data['password']
            password2 = form.cleaned_data['password2']
            timezone = form.cleaned_data['timezone']
            if check_password(password2, user.password):
                user.name = name
                user.timezone = timezone
                if password is not ('' or None):
                    user.password = make_password(password, salt=name+'connect2', hasher='default')
                user.save()
                request.session['user'] = user.email
                return redirect('/myaccount/')
            else:
                context.update({"error": "Your password was not recognised"})
                context['account_form'] = form
                return render(request,'templates/account_edit.html', context)
    else:
        form = EditAccountForm(initial=data)
    context['account_form'] = form
    return render(request,'templates/account_edit.html', context)


@csrf_exempt
def getAvgElec(request):
    if request.method == 'GET':
        user = check_auth(request)
        channel = user.prefered_channel
        if channel:
            sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Electricity')
            since = Data.objects.all().filter(sensor__in=sensors).order_by('date').last().date
            data = Data.objects.all().filter(sensor__in=sensors).aggregate(Avg('value'))['value__avg']
            body = '{"data": "%.2f", "since": "%s"}' %(data, since)
            response = HttpResponse(body, content_type="text/plain")

        return response

@csrf_exempt
def getCurrentElec(request):
    if request.method == 'GET':
        user = check_auth(request)
        channel = user.prefered_channel
        if channel:
            sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Electricity')
            value = Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value
            response = HttpResponse(value, content_type="text/plain")

        return response

@csrf_exempt
def getElec(request):
    if request.method == 'GET':
        user = check_auth(request)
        channel = user.prefered_channel
        if channel:
            sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Electricity')
            maximum = Data.objects.all().filter(sensor__in=sensors).aggregate(Max('value'))['value__max']
            minimum = Data.objects.all().filter(sensor__in=sensors).aggregate(Min('value'))['value__min']
            data = Data.objects.all().filter(sensor__in=sensors)
            array = []
            for d in data:
                array.append([d.date.toordinal(), d.value, maximum, minimum, 8])
            print array
            response = HttpResponse([array], content_type="text/plain")

        return response

#shows my channels page if user, else signin page
def mychannels(request):
    context = {"page":"mychannels"}
    user = check_auth(request)
    context.update({"user":user.email})
    channels = Channel.objects.filter(user=user)
    context.update({"channels":channels})
    return render(request,'templates/mychannels.html', context)

def setpreferedchannel(request):
    user = check_auth(request)
    user.prefered_channel=request.GET["channel"]
    user.save()
    return redirect('/dashboard')

#show createchannel page
def newchannel(request):
    context = {"page":"newchannel"}
    user = check_auth(request)
    context.update({"user": user.email})

    if request.method == 'POST':
        form = NewChannelForm(request, data=request.POST)    
            
        is_valid = form.is_valid()
        print(is_valid)
        if is_valid:

            name = form.cleaned_data['name']
            chosensensors = form.cleaned_data['chosensensors']
            print(chosensensors)
            channel = Channel(name=name, API_KEY=hashlib.md5( str(random.getrandbits(256)) ).hexdigest(), user=user)
            print(hashlib.md5( str(random.getrandbits(256))))
            for s in chosensensors:
                channel.sensors.add(s)
            channel.save()
            return login(request, user)
    else:
        form = NewChannelForm()
    context['NewChannelForm'] = form
    form.fields['chosensensors'].queryset = Sensor.objects.filter(user=user)
    return render(request,'templates/newchannel.html', context)

#shows electricity page
def electricity(request):
    context = {"page":"electricity"}
    user = check_auth(request)
    channel = user.prefered_channel
    context.update({"user": user.email})
    if channel:
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Electricity')
        context.update({"currentElectricity": Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value})
        context.update({"averageElectricity": Data.objects.all().filter(sensor__in=sensors).aggregate(Avg('value'))['value__avg']})
        context.update({"since": Data.objects.all().filter(sensor__in=sensors).order_by('date').last().date})
    return render(request,'templates/electricity.html', context)

#shows water page
def water(request):
    context = {"page":"water"}
    user = check_auth(request)
    context.update({"user": user.email})
    channel = user.prefered_channel
    if channel:
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Water')
        context.update({"water": Data.objects.all().filter(sensor__in=sensors).aggregate(Sum('value'))['value__sum']})
        context.update({"since": Data.objects.all().filter(sensor__in=sensors).order_by('date').last().date})
    return render(request,'templates/water.html', context)

#shows photovoltaic page
def photovoltaic(request):
    context = {"page":"photovoltaic"}
    user = check_auth(request)
    context.update({"user": user.email})
    return render(request,'templates/photovoltaic.html', context)

#shows weather page
def weather(request):
    context = {"page":"weather"}
    user = check_auth(request)
    context.update({"user": user.email})
    channel = user.prefered_channel
    if channel:
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Temperature')
        context.update({"temp": Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value})
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Humidity')
        context.update({"humidity": Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value})
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Pressure')
        context.update({"pressure": Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value})
        sensors = Sensor.objects.all().filter(channels=channel, user=user, TYPE='Luminosity')
        context.update({"luminosity": Data.objects.all().filter(sensor__in=sensors).order_by('date').first().value})
    return render(request,'templates/weather.html', context)

#shows forecast page
def forecast(request):
    context = {"page":"forecast"}
    user = check_auth(request)
    context.update({"user": user.email})
    return render(request,'templates/forecast.html', context)

#shows advanced page
def advanced(request):
    context = {"page":"advanced"}
    user = check_auth(request)
    context.update({"user": user.email})
    return render(request,'templates/advanced.html', context)

#shows new sensor page page
def newsensors(request):
    context = {"page":"newsensors"}
    user = check_auth(request)
    context.update({"user": user.email})
    if request.method == 'POST':
        form = SensorForms(request, data=request.POST)
        form2 = BridgeForms(request, data=request.POST)
            
        is_valid = form.is_valid()

        if is_valid:
            name = form.cleaned_data['name']
            bridge = form.cleaned_data['bridge']
            networkid = form.cleaned_data['NETWORKID']
            nodeid = form.cleaned_data['NODEID']
            Type = form.cleaned_data['TYPE']
            version = form.cleaned_data['VERSION']
            sensor = Sensor(name=name, user=user, bridge=bridge, NETWORKID=networkid, NODEID=nodeid, TYPE=Type, VERSION=version)
            sensor.save()
            return redirect('sensors')
    else:
        form = SensorForms()
        form2 = BridgeForms()
    form.fields['bridge'].queryset = Bridge.objects.filter(user=user)
    context['form'] = form
    context['form2'] = form2
    return render(request,'templates/new_sensors.html', context)

#shows newbridge page
def newbridge(request):
    context = {"page":"newbridge"}
    user = check_auth(request)
    context.update({"user": user.email})
    if request.method == 'POST':
        form = BridgeForms(request, data=request.POST)
            
        is_valid = form.is_valid()

        if is_valid:
            name = form.cleaned_data['name']
            networkid = form.cleaned_data['NETWORKID']
            nodeid = form.cleaned_data['NODEID']
            version = form.cleaned_data['VERSION']
            bridge = Bridge(name=name, user=user, NETWORKID=networkid, NODEID=nodeid, VERSION=version)
            bridge.save()
            return redirect('sensors')
    else:
        form = SensorForms()
    context['form'] = form
    return render(request,'templates/new_sensors.html', context)

#shows sensors
def sensors(request):
    context = {"page":"newsensors"}
    user = check_auth(request)
    context.update({"user": user.email})
    context.update({"sensors": Sensor.objects.all().filter(user=user)})
    context.update({"bridges": Bridge.objects.all().filter(user=user)})
    return render(request,'templates/sensors.html', context)

#return the ID of a prob
def getID(identification):
    ID = identification[1:identification.index('-')]
    remaining = identification[identification.index('-')+1:]
    NETWORDID = remaining[:remaining.index('-')]
    remaining = remaining[remaining.index('-')+1:]
    GATEWAY = remaining[:remaining.index('-')]
    remaining = remaining[remaining.index('-')+1:]
    NODEID = remaining[:remaining.index('-')]
    remaining = remaining[remaining.index('-')+1:]
    TYPE = remaining[:remaining.index('-')]
    remaining = remaining[remaining.index('-')+1:]
    VERSION = remaining[:-1]
    return [ID, NETWORDID, GATEWAY, NODEID, TYPE, VERSION]

@csrf_exempt
def post_data(request):
    if request.method == 'POST':
        value = request.POST['data']
        print request.POST['id']
        identification = getID(request.POST['id'])
        sensor = Sensor.objects.get(name=identification[0])
        if sensor.NETWORKID is not identification[1] or sensor.bridge is not identification[2] or sensor.NODEID is not identification[3] or sensor.TYPE is not identification[4] or sensor.VERSION is not identification[5]:
            sensor.NETWORKID = identification[1]
            sensor.bridge = Bridge.objects.get(name=identification[2])
            sensor.NODEID = identification[3]
            sensor.TYPE = identification[4]
            sensor.VERSION = identification[5]
            sensor.save()
        data = Data(sensor=Sensor.objects.get(name=identification[0]), value=value)
        data.save()
    else:
        return redirect('/')
    return HttpResponse("OK")

@csrf_exempt
def post_Version_Bridge(request):
    if request.method == 'POST':
        identification = getID(request.POST['id'])
        bridge = Bridge.objects.get(name=identification[0])

        if bridge.VERSION is not identification[5] or bridge.NODEID is not identification[3] or bridge.VERSION is not identification[5]:
            bridge.NETWORKID = identification[1]
            bridge.NODEID = identification[3]
            bridge.VERSION = identification[5]
            bridge.save()

        if bridge.VERSION is not Version.objects.get(TYPE="Bridge"):
            response = HttpResponse(content_type='application/force-download')
            response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('flash.hex')
            response['X-Sendfile'] = smart_str('versions/bridge.hex')
            return response
    else:
        return redirect('/')
    return HttpResponse("OK")

@csrf_exempt
def post_Version_Probes(request):
    if request.method == 'POST':
        identification = getID(request.POST['id'])
        bridge = Bridge.objects.get(name=identification[0])
        probes = Sensor.objects.filter(bridge=bridge)

        for p in probes:
            print Version.objects.get(TYPE=p.TYPE)
            if p.VERSION is not Version.objects.get(TYPE=p.TYPE):
                response = HttpResponse(content_type='application/force-download')
                response['HTTP_ACCEPT_LANGUAGE'] =  p.NODEID
                response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('flash.hex')
                response['X-Sendfile'] = smart_str('versions/%s.hex' % p.TYPE)
                return response
    else:
        return redirect('/')
    return HttpResponse("OK")
