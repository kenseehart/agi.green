<template>
    <Vueform v-bind="vueform" @change="handleChange" />
</template>

<script>
import { Vueform } from '@vueform/vueform';
import jsYaml from 'js-yaml';
import { ref, watch, inject } from 'vue';

export default {
    components: {
        Vueform,
    },
    props: ['yamlSchema', 'jsonSchema'],
    setup(props) {
        const vueform = ref({
            schema: {},
        });
        const send_ws = inject('send_ws'); // Inject the WebSocket send function

        const handleChange = (e) => {
            // Get the schema for the changed field
            const fieldName = Object.keys(e).find(key => key !== 'form_id');
            const schema = vueform.value.schema[fieldName];
            
            console.log('Change event:', e);
            console.log('Field schema:', schema);
            
            // Check if the changed element has ws_send property
            if (schema?.ws_send) {
                const formData = {
                    cmd: schema.ws_send,
                    form_id: e.form_id,
                    data: e
                };
                
                console.log('Sending WS message:', formData);
                window.send_ws(formData.cmd, formData);
            }
        };

        // Existing watchers
        watch(() => props.yamlSchema, (newVal) => {
            if (newVal) {
                const content = jsYaml.load(newVal);
                content.schema.form_id = {
                    type: 'hidden',
                    default: content.id,
                };
                console.log('YAML', content);
                vueform.value.schema = content.schema;
            }
        }, { immediate: true });

        watch(() => props.jsonSchema, (newVal) => {
            if (newVal) {
                const content = JSON.parse(newVal);
                content.schema.form_id = {
                    type: 'hidden',
                    default: content.id,
                };
                console.log('JSON:', content);
                vueform.value.schema = content.schema;
            }
        }, { immediate: true });

        return { 
            vueform,
            handleChange
        };
    },
};
</script>



