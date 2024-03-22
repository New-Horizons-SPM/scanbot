export const checkHook = async (hook) => {
    const response = await fetch("/check_hook", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({hook: hook}),
    })
    
    const data = await response.json()
    return data['status']
}

export const is_auto_init = async () => {
    const response = await fetch("/is_auto_init")
    const data = await response.json()
    return data['status']
}

export const getResponse = async (point) => {
	const response = await fetch(point)
	const data = await response.json()
    return data['status']
}

export const positiveInt = (test) => {
    var result = /^\d*$/.test(test) || !(test)
    if(result) {
        return !/-/.test(test)
    }
    return false
}

export const integer = (test) => {
    return /^-?\d*$/.test(test) || !(test)
}

export const positiveNumber = (test) => {
    var result = /\d+(\.\d*)?$/.test(test) || !(test)
    if(result) {
        return !/-/.test(test)
    }
    return false
}

export const number = (test) => {
    return /^(-?\d+(\.\d*)?|\.\d+)?$/.test(test) || !(test) || test === '-'
}