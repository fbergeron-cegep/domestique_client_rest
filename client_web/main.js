async function chargerTaches(){
    const taches = await getTaches();
    remplirTableauTaches(taches);
}

async function getTaches(){
    const temp = await fetch('/api/taches');
    return await temp.json();
}

async function reinitialiser(){
    await fetch('/reinitialiser', {
        method: 'PATCH'
    });
    await chargerTaches();
}

async function supprimerTache(id){
    await fetch('/api/taches/' + id, {
        method: 'DELETE'
    } );
    await chargerTaches();
}

async function modifierTache(nom, due, id){
    const data = {"nom_tache": nom.value, "due_pour": due.value};
    const body = JSON.stringify(data);

    await fetch('/api/taches/' + id, {
        method: 'PUT',
        body: body,
        headers: {
			"Content-Type": "application/json",
			"Accept": "application/json"
		}
    } );
    await chargerTaches();
}

async function convertirTachePourEdition(ligne, tache){
    const tds = ligne.childNodes;

    const inputNom = document.createElement('input');
    inputNom.type = 'text';
    inputNom.name = 'nom_tache';
    inputNom.value = tache.nom_tache;

    tds[1].replaceChildren(inputNom);

    const inputDue = document.createElement('input');
    inputDue.type = 'text';
    inputDue.name = 'due_pour';
    inputDue.value = tache.due_pour;

    tds[2].replaceChildren(inputDue);

    const btnAnnuler = document.createElement("button");
    btnAnnuler.innerHTML = "Annuler";
    btnAnnuler.onclick = () => {
        chargerTaches();
    };

    const btnSoumettre = document.createElement('button');
    btnSoumettre.innerText = "Modifier";
    btnSoumettre.onclick = function(){
        modifierTache(inputNom, inputDue, tache.rowid);
    };

    tds[3].replaceChildren(btnAnnuler, btnSoumettre);
}

function remplirTableauTaches(taches){
    const tableau = document.getElementById('tableau-taches');
    const entete = document.getElementById('tableau-taches-entete');

    tableau.replaceChildren(entete);

    taches.forEach(function(tache){
        const tdID = document.createElement('td');
        const tdNom = document.createElement('td');
        const tdEcheance = document.createElement('td');
        const tdActions = document.createElement('td');

        const tr = document.createElement('tr');
        tr.append(tdID, tdNom, tdEcheance, tdActions);

        tdID.innerText = tache.rowid;
        tdNom.innerText = tache.nom_tache;
        tdEcheance.innerText = tache.due_pour;

        const btnSupprimer = document.createElement('button');
        btnSupprimer.innerHTML = 'Supprimer';
        btnSupprimer.onclick = function(){
            supprimerTache(tache.rowid);
            return false;
        };
        tdActions.append(btnSupprimer);

        const btnModifier = document.createElement('button');
        btnModifier.innerHTML = 'Modifier';
        btnModifier.onclick = function(){
            convertirTachePourEdition(tr, tache);
        };
        tdActions.append(btnModifier);

        tableau.append(tr);
    });
}

async function ajouterTache(e){
    e.preventDefault();

    const form = e.currentTarget;
    const data = new FormData(form);

    const body = JSON.stringify(Object.fromEntries(data));
    const options = {
        method: 'POST',
        body: body,
        headers: {
			"Content-Type": "application/json",
			"Accept": "application/json"
		}
    };
    await fetch(form.action, options);
    await chargerTaches(); //Mettre à jour le tableau
    form.reset();
}

document.addEventListener("DOMContentLoaded", async function (){
    const btnInit = document.getElementById('btnInit');
    btnInit.addEventListener('click', reinitialiser);

    await chargerTaches();

    const formTache = document.getElementById('form-ajout-tache');
    formTache.addEventListener('submit', await ajouterTache);
});


