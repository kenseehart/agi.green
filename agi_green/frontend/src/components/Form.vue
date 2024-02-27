<template>
    <VueJsonSchemaForm :schema="formSchema" @submit="onFormSubmit" />
</template>

<script>
import VueJsonSchemaForm from '@lljj/vue-json-schema-form';

export default {
    components: {
        VueJsonSchemaForm,
    },
    props: ['formSchema'],
    methods: {
        onFormSubmit(formData) {
            // Handle form data submission here
            console.log('Form submitted with data:', formData);
        },
    },
};
</script>
