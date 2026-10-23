// Enhance existing forms without replacing server validation or finance request keys.
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('label:not([for])').forEach((label,index)=>{
    if(label.querySelector('input,select,textarea'))return;
    const field=label.nextElementSibling;
    if(field?.matches('input,select,textarea')){field.id=field.id||`labelled-field-${index}`;label.htmlFor=field.id}
  });
  for(const id of ['bookingForm','serviceUsageForm','roomForm','customerForm','serviceForm']){
    const form=document.getElementById(id),work=form?.onsubmit;
    if(!work||work.constructor.name!=='AsyncFunction')continue;
    form.onsubmit=async event=>{
      if(form.dataset.busy==='1'){event.preventDefault();return}
      form.dataset.busy='1';form.setAttribute('aria-busy','true');
      const buttons=[...form.querySelectorAll('button[type=submit],button:not([type])')],states=buttons.map(b=>b.disabled);
      buttons.forEach(b=>b.disabled=true);
      try{return await work.call(form,event)}finally{delete form.dataset.busy;form.removeAttribute('aria-busy');buttons.forEach((b,i)=>b.disabled=states[i])}
    };
  }
  const sidebar=document.getElementById('sidebar'),menu=document.getElementById('menuBtn');
  menu?.setAttribute('aria-controls','sidebar');menu?.setAttribute('aria-expanded','false');
  menu?.addEventListener('click',()=>menu.setAttribute('aria-expanded',String(sidebar.classList.contains('mobile-open'))));
  document.addEventListener('click',event=>{if(window.innerWidth<=760&&!sidebar?.contains(event.target)&&!menu?.contains(event.target)){sidebar?.classList.remove('mobile-open');menu?.setAttribute('aria-expanded','false')}});
});
