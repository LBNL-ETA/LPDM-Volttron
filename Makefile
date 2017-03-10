IMG_NAME=cberd-image
CONTAINER_NAME = cberd-container
CONTAINER_USER = volttron_user

clone_lpdm:
	git clone git@github.com:LBNL-ETA/LPDM.git -b develop

#clone_volttron:
#	git clone git@github.com:VOLTTRON/volttron.git -b releases/4.0.1

update_lpdm_volttron:
	git pull

#clone_repos: clone_lpdm clone_volttron

build:
	docker build -t=${IMG_NAME} .

full_rebuild:clean_all clone_lpdm
	docker build -t=${IMG_NAME} --rm=true --no-cache .

run:
	docker run -ti --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}/LPDM-Volttron:/home/${CONTAINER_USER}/LPDM-Volttron \
	-v ${CURDIR}/LPDM:/home/${CONTAINER_USER}/LPDM \
	${IMG_NAME}

.PHONY : clean
clean:
	rm -rf LPDM
#	rm -rf volttron

clean_all: clean
	docker rmi ${IMG_NAME}
